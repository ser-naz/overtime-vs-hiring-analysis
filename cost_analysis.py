import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

# Import plotting function from visualization module
from visualization import plot_costs

pd.set_option("display.width", 1000)
pd.set_option("display.max_columns", None)

"""
Overtime vs Hiring Analysis

This model compares two options when workload increases:
- pay overtime to current employees
- hire one additional full-time employee

It calculates total weekly labor cost under both scenarios
and identifies the break-even point where hiring becomes cheaper.
"""

# ----------------------------------------------------------------------------------------------------------------------
# Connect to PostgreSQL and load tables

# Read database credentials from an external file.
# The config folder should NOT be pushed to GitHub.
credentials = {}

with open("config/db_credentials.txt", "r") as file:
    for line in file:
        key, value = line.strip().split("=")
        credentials[key] = value

# Extract database connection values from the credentials dictionary.
user = credentials.get("DB_USER")
password = credentials.get("DB_PASSWORD")
host = credentials.get("DB_HOST")
port = credentials.get("DB_PORT")
db = credentials.get("DB_NAME")

# Encode the password so special characters do not break the connection string.
encoded_password = urllib.parse.quote_plus(password)

# Create PostgreSQL connection engine.
connection_string = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{db}"
engine = create_engine(connection_string)


# Load source tables from PostgreSQL into pandas DataFrames.
# CSV versions of these tables are available in the /data folder for reference and reproducibility.
df_employees = pd.read_sql("SELECT * FROM employees", engine)
df_cost = pd.read_sql("SELECT * FROM cost_assumptions", engine)
df_scenarios = pd.read_sql("SELECT * FROM workload_scenarios", engine)

# ----------------------------------------------------------------------------------------------------------------------
# Prepare model inputs

# Count employees eligible for overtime.
# Boolean values behave like numbers in pandas:
# True = 1, False = 0.
ot_eligible_count = df_employees["ot_eligible"].sum()

# Extract hourly rate for junior employees.
# This model assumes all junior employees have the same hourly rate.
junior_rates = df_employees.loc[
    df_employees["role"] == "junior", "hourly_rate"
].unique()

# Validate the assumption that all juniors have one consistent rate.
# If multiple junior rates exist, the model should stop instead of producing misleading results.
if len(junior_rates) != 1:
    raise ValueError("Expected all junior employees to have the same hourly rate.")

junior_rate = junior_rates[0]

# Extract cost assumptions from the cost_assumptions table.
# These values drive the cost comparison.
tax_rate = df_cost["employer_tax_rate"].iloc[0]
ot_multiplier = df_cost["overtime_multiplier"].iloc[0]
health_insurance = df_cost["health_insurance_weekly"].iloc[0]

# Standard full-time weekly hours per employee.
regular_hours_per_employee = 40

# Current regular capacity before overtime starts.
# Only OT-eligible junior employees are considered in this model.
regular_capacity = ot_eligible_count * regular_hours_per_employee

# Capacity after hiring one additional full-time employee.
# Current capacity: 11 employees × 40 hours = 440
# After hiring: 12 employees × 40 hours = 480
full_capacity_with_hire = (ot_eligible_count + 1) * regular_hours_per_employee

# ----------------------------------------------------------------------------------------------------------------------
# Functions

def calculate_overtime_hours(scenarios, capacity):
    """
    Calculate regular and overtime hours for each workload scenario.

    Parameters:
    scenarios: DataFrame containing workload scenarios
    capacity: current regular capacity before overtime starts

    Returns:
    DataFrame with added regular_hours and overtime_hours columns
    """

    # Create a copy to avoid modifying the original DataFrame directly.
    df = scenarios.copy()

    # Overtime hours:
    # If required hours exceed current regular capacity, the excess becomes overtime.
    # If required hours are within capacity, overtime is 0.
    df["overtime_hours"] = (
        df["required_hours_per_week"] - capacity
    ).clip(lower=0)

    # Regular hours:
    # Regular hours cannot exceed current regular capacity.
    # Example: if capacity is 440 and workload is 460,
    # regular hours stay at 440 and the remaining 20 are overtime.
    df["regular_hours"] = df["required_hours_per_week"].clip(upper=capacity)

    return df


def calculate_costs(
    df,
    junior_rate,
    tax_rate,
    ot_multiplier,
    health_insurance,
    full_capacity_with_hire
):
    """
    Calculate labor cost under two scenarios:
    1. Current staff + overtime
    2. Hire one additional full-time employee

    Returns:
    DataFrame with wage, cost, difference, and decision columns
    """

    # Create a copy to avoid modifying the original DataFrame directly.
    df = df.copy()

    # ------------------------------------------------------------------------------------------------------------------
    # Overtime scenario

    # Regular wages are based on regular hours only.
    df["regular_wages"] = df["regular_hours"] * junior_rate

    # Overtime wages are paid at the overtime premium rate.
    # Example: $20 hourly rate × 1.5 = $30 overtime rate.
    df["ot_wages"] = df["overtime_hours"] * junior_rate * ot_multiplier

    # Total wages in the overtime scenario.
    df["total_wages_ot"] = df["regular_wages"] + df["ot_wages"]

    # Employer payroll taxes apply to both regular wages and overtime wages.
    df["overtime_total_cost"] = df["total_wages_ot"] * (1 + tax_rate)

    # ------------------------------------------------------------------------------------------------------------------
    # Hiring scenario

    # Hiring one full-time employee means paying for the full additional 40 hours.
    # In this model:
    # current junior capacity = 440 hours
    # capacity with one new hire = 480 hours
    # Therefore, hiring paid hours are fixed at 480 for all scenarios.
    df["paid_hours_hiring"] = full_capacity_with_hire

    # Hiring scenario wages are based on 12 junior employees working 40 hours each.
    df["total_wages_hiring"] = df["paid_hours_hiring"] * junior_rate

    # Employer payroll taxes apply to hiring wages.
    # Health insurance is added as a fixed weekly employer-paid benefit.
    df["hiring_total_cost"] = (
        df["total_wages_hiring"] * (1 + tax_rate)
        + health_insurance
    )

    # ------------------------------------------------------------------------------------------------------------------
    # Comparison

    # Difference:
    # positive value → hiring is more expensive
    # negative value → hiring is cheaper
    df["cost_difference"] = df["hiring_total_cost"] - df["overtime_total_cost"]

    # Decision logic:
    # Baseline has no overtime, so no staffing change is needed.
    # If hiring is cheaper, decision = Hire.
    # Otherwise, decision = Overtime.
    df["decision"] = df.apply(
        lambda row: "No action" if row["overtime_hours"] == 0
        else ("Hire" if row["cost_difference"] < 0 else "Overtime"),
        axis=1
    )

    return df


# ----------------------------------------------------------------------------------------------------------------------
# Run analysis

# Convert workload scenarios into regular and overtime hours.
df_scenarios = calculate_overtime_hours(df_scenarios, regular_capacity)

# Calculate overtime cost, hiring cost, cost difference, and decision.
df_scenarios = calculate_costs(
    df_scenarios,
    junior_rate,
    tax_rate,
    ot_multiplier,
    health_insurance,
    full_capacity_with_hire
)

# ----------------------------------------------------------------------------------------------------------------------
# Break-even analysis

# Calculate break-even overtime hours.
# This is the point where: cost of overtime = cost of hiring one additional employee

break_even_ot_hours = (
    # Total weekly cost of hiring one employee:
    # 40 regular hours × hourly rate + employer taxes + health insurance
    (regular_hours_per_employee * junior_rate * (1 + tax_rate) + health_insurance)

    # Divided by cost of one overtime hour including employer taxes
    / (junior_rate * ot_multiplier * (1 + tax_rate))
)

# ----------------------------------------------------------------------------------------------------------------------
print(df_scenarios)

print(f"Overtime is cheaper below {break_even_ot_hours:.2f} OT hours per week, hiring is cheaper above it.")

# Output
# scenario_id scenario_name  required_hours_per_week  overtime_hours  regular_hours  regular_wages  ot_wages  total_wages_ot  overtime_total_cost  paid_hours_hiring  total_wages_hiring  hiring_total_cost  cost_difference   decision
# 0            1      Baseline                      440               0            440         8800.0       0.0          8800.0               9592.0                480              9600.0            10604.0           1012.0  No action
# 1            2   Increase +5                      445               5            440         8800.0     150.0          8950.0               9755.5                480              9600.0            10604.0            848.5   Overtime
# 2            3  Increase +10                      450              10            440         8800.0     300.0          9100.0               9919.0                480              9600.0            10604.0            685.0   Overtime
# 3            4  Increase +15                      455              15            440         8800.0     450.0          9250.0              10082.5                480              9600.0            10604.0            521.5   Overtime
# 4            5  Increase +20                      460              20            440         8800.0     600.0          9400.0              10246.0                480              9600.0            10604.0            358.0   Overtime
# 5            6  Increase +25                      465              25            440         8800.0     750.0          9550.0              10409.5                480              9600.0            10604.0            194.5   Overtime
# 6            7  Increase +30                      470              30            440         8800.0     900.0          9700.0              10573.0                480              9600.0            10604.0             31.0   Overtime
# 7            8  Increase +35                      475              35            440         8800.0    1050.0          9850.0              10736.5                480              9600.0            10604.0           -132.5       Hire
# 8            9  Increase +40                      480              40            440         8800.0    1200.0         10000.0              10900.0                480              9600.0            10604.0           -296.0       Hire
# Overtime is cheaper below 30.95 OT hours per week, hiring is cheaper above it.


# ----------------------------------------------------------------------------------------------------------------------
# Call the visualization function using the prepared inputs:
# - df_scenarios: contains workload levels and calculated costs for both strategies
# - break_even_ot_hours: analytical result showing the OT threshold where hiring becomes cheaper
# - regular_capacity: baseline capacity (e.g., 440 hours), used to convert OT hours into total workload
#
# it shows how costs behave and where the strategy should change.
plot_costs(df_scenarios, break_even_ot_hours, regular_capacity)
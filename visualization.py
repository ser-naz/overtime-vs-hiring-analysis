import matplotlib.pyplot as plt


def plot_costs(df_scenarios, break_even_ot_hours, regular_capacity):
    # Convert break-even overtime hours into total required workload.
    # Example:
    # regular capacity = 440 hours
    # break-even OT hours ≈ 30.95
    # break-even workload ≈ 470.95 required hours
    break_even_x = regular_capacity + break_even_ot_hours

    # Hiring cost is fixed in this model because hiring adds one full-time employee.
    # The company pays for 480 hours regardless of whether workload is 445 or 480.
    break_even_y = df_scenarios["hiring_total_cost"].iloc[0]

    plt.figure(figsize=(10, 6))

    # Overtime cost increases as workload increases.
    # Each additional hour above regular capacity is paid at the overtime rate.
    plt.plot(
        df_scenarios["required_hours_per_week"],
        df_scenarios["overtime_total_cost"],
        label="Overtime Cost"
    )

    # Hiring cost is flat because the new employee is treated as a fixed weekly cost.
    plt.plot(
        df_scenarios["required_hours_per_week"],
        df_scenarios["hiring_total_cost"],
        label="Hiring Cost"
    )

    # Vertical line marks the exact workload level where OT cost equals hiring cost.
    plt.axvline(
        x=break_even_x,
        linestyle="--",
        label=f"Break-even ({break_even_x:.0f} hrs)"
    )

    # Mark the intersection point between the two cost strategies.
    plt.scatter(break_even_x, break_even_y)

    # Label the break-even point slightly below the hiring cost line.
    plt.text(
        break_even_x + 0.5,
        break_even_y - 40,
        "Break-even"
    )

    # Add business interpretation directly on the chart.
    # Left of break-even: overtime is cheaper.
    # Right of break-even: hiring is cheaper.
    plt.annotate("OT cheaper", xy=(450, 10000))
    plt.annotate("Hiring cheaper", xy=(475, 10800))

    plt.xlabel("Required Hours per Week")
    plt.ylabel("Total Weekly Cost ($)")
    plt.title("Overtime vs Hiring: Cost Comparison and Break-even Point")

    plt.xlim(440, 480)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # save a plot in visualization_output
    plt.savefig("visualization_output/cost_comparison.png", dpi=300, bbox_inches="tight")

    plt.show()
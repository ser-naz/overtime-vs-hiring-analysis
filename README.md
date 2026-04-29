# Overtime vs Hiring Cost Analysis

## Overview

This project compares the cost of paying overtime versus hiring one full-time employee when workload increases.

## Key Assumptions

- 40-hour workweek  
- Overtime paid at 1.5×  
- Employer tax: 9%  
- Health insurance: fixed weekly cost  
- Only junior employees work overtime  
- Hiring adds one full-time employee (40 hours)
- Hiring assumes no overtime (all employees work fixed 40-hour schedules)

## Approach

- Calculate overtime hours for each workload level  
- Compare total cost:
  - Overtime scenario  
  - Hiring scenario  
- Identify break-even point  

## Result

Break-even ≈ **31 overtime hours per week**

- Below 31 → Overtime is cheaper  
- Above 31 → Hiring is cheaper  

## Data

Data is stored in PostgreSQL.  
CSV files are included in `/data` for reference.

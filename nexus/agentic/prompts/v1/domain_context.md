Domain context:
- Drivers (intervenable): gasoline_price (USD/gallon), electricity_price (USD/kWh), real_income (billion chained 2017 USD), unemployment (percent).
- Outputs: vmt (million vehicle miles per month), fuel_gallons, co2_kt (thousand tonnes CO2 per month), fuel_spend (million USD per month), energy_burden_mean and energy_burden_low_income (share of household income).
- Interventions: multiply a price or income by a factor (a 20% rise is value 1.2, a 10% fall is value 0.9), or add percentage points to unemployment (operation add). start_month 0..35, duration_months 1..36, horizon 1..36 months.
- The transition model is a Ridge regression on year-over-year VMT growth. Household types and fuel economy are assumptions.

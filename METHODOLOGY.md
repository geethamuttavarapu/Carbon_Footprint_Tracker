# Calculation assumptions (current prototype)

The calculator produces an indicative daily total in kg CO2e. It is not a validated life-cycle assessment and should not be used as a certified footprint, audit, regulatory filing or precise comparison between users.

| Input | Prototype assumption |
|---|---:|
| Car travel | 0.18 kg CO2e per km, divided by car occupants (defaults to 1) |
| Motorcycle travel | 0.0356 kg CO2 per km (India GHG Program, motorcycle under 135 cc with 10% uplift; older 2014-15 study) |
| Bus travel | 0.015161 kg CO2 per passenger-km (India GHG Program intracity bus estimate; older study) |
| Train travel | 0.00794 kg CO2 per passenger-km (India GHG Program non-suburban rail estimate; older study) |
| Metro travel | 0.04 kg CO2e per km |
| Bicycle / walking / work from home | 0 kg CO2e per km |
| Daily meals: plant-based / vegetarian / mixed / meat-heavy | 1.10 / 1.35 / 1.80 / 2.50 kg CO2e per day (illustrative category constants) |
| Household electricity | 0.727 kg CO2 per kWh, divided by household size; renewable-energy selection applies a 0.35 multiplier (CEA all-India grid weighted average, FY 2023-24) |
| Shopping | 0.45 kg CO2e for Yes; 0.05 kg CO2e for No |
| Waste | 0.05 / 0.12 / 0.22 / 0.12 kg CO2e for mostly recycled / some recycled / mostly landfill / not sure |
| Cooking | 0.18 / 0.12 / 0.15 / 0.16 / 0.15 kg CO2e for LPG / electricity / PNG / other / not sure |

The profile's Vegan setting changes the mixed-meal assumption to 1.30. Daily category selections otherwise determine the meal value. City, home type and usual transport are collected as profile context but are not directly applied as regional emission factors. Car occupancy is collected as an optional profile field and defaults to one occupant. The renewable-electricity multiplier is a simplifying user-selected assumption, not a measured supplier-specific renewable share.

The electricity factor is taken from the Central Electricity Authority (CEA), Government of India, Annual Report 2024-25: the all-India grid emission factor including renewable generation was 0.727 tCO2/MWh for FY 2023-24 (numerically 0.727 kg CO2/kWh). This is a location-based grid CO2 factor, not a complete lifecycle CO2e factor. Motorcycle, intracity bus and non-suburban rail use older India GHG Program estimates (2014-15 technical papers); their age and boundaries limit current representativeness. Car and metro remain illustrative because the app does not collect enough vehicle-specific or metro-system data. Food, shopping, waste and cooking remain illustrative prototype values and are not certified India-specific factors. The supplied `ghg-conversion-factors.xlsx` file is a UK Government 2023 conversion-factor workbook retained from the original project; it is not used as Indian data.

For a research-grade release, replace each assumption with traceable, current factors appropriate to India and the relevant activity boundary. Record the source organisation, publication year, geography, units, gases included, lifecycle boundary and uncertainty. Validate the resulting model against an established calculator or measured activity data, and show uncertainty ranges to users.


## Sources
- Central Electricity Authority, Government of India, *Annual Report 2024-25*, section 2.11.1 / page 23, FY 2023-24 all-India grid emission factor series. CEA reports 0.727 tCO2/MWh for FY 2023-24. https://www.cea.nic.in/api/dashboardReports/view-pdf/en/62d073ce-f773-469e-acc7-366113cbbd5f
- CEA CDM-CO2 Baseline Database releases and user guides: https://cea.nic.in/cdm-co2-baseline-view?lang=en&mappingId=234
- India GHG Program, *Transport Emission Factors* (links to 2015 India-specific road and rail technical papers): https://indiaghgp.org/transport-emission-factors

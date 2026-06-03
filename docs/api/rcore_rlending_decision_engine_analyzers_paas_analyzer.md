# API Reference: paas_analyzer

Source file: `rcore/rlending/decision_engine/analyzers/paas_analyzer.py`

## Classes

### class `PaasOrderAnalyzer`
A service to analyze a customer's PaaS wallet history from the ERPNext system
and calculate key metrics.

#### Documented Internal Methods
##### `analyze(self)`
Main method to trigger the analysis process.

##### `_calculate_metrics(self)`
Calculates key metrics from the fetched wallet history data.

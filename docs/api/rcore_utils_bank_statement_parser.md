# API Reference: bank_statement_parser

Source file: `rcore/utils/bank_statement_parser.py`

## Classes

### class `BankStatementParser`
A service to parse uploaded bank statements (CSV format) and extract key financial metrics.

#### Documented Internal Methods
##### `parse(self)`
Main method to trigger the parsing process based on the file type.

##### `_calculate_metrics(self)`
Calculates key financial metrics from the parsed transaction data.

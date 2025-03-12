# Binance Trade Data Aggregator

This package provides tools to aggregate and analyze Binance ETH/USDT trade data from Parquet files.

## Installation

You can install the package directly from the source:

```bash
cd binance_trade_aggregator
pip install -e .
```

## Usage

### Command-line Script

After installation, you can use the `aggregate-trades` command:

```bash
# Load trades for a specific month
aggregate-trades 2023-01

# Load trades for a date range
aggregate-trades 2023-01 --end_date 2023-02

# Load specific columns only
aggregate-trades 2023-01 --columns price time

# Apply sampling to reduce memory usage
aggregate-trades 2023-01 --sample_rate 0.01

# Save output to a file
aggregate-trades 2023-01 --output trades_2023_01.parquet

# Specify a custom trades directory
aggregate-trades 2023-01 --trades_dir /path/to/trades
```

### Python Module

```python
from binance_trade_aggregator import TradeAggregator

# Create an instance of the TradeAggregator
aggregator = TradeAggregator()

# Get available dates
dates = aggregator.get_available_dates()
print(f"Available dates: {dates}")

# Load trades for a specific month
df = aggregator.load_trades("2023-01")

# Load trades for a date range with sampling
df = aggregator.load_trades("2023-01", "2023-02", sample_rate=0.01)

# Load specific columns only
df = aggregator.load_trades("2023-01", columns=['price', 'time'])
```

## Examples

Check the `examples` directory for more detailed examples:

```bash
cd examples
python example_usage.py
```

## Data Structure

The Parquet files contain the following columns:

- `id`: Trade ID
- `price`: Trade price in USDT
- `qty`: Trade quantity in ETH
- `quote_qty`: Trade value in USDT (price * qty)
- `time`: Timestamp in milliseconds
- `is_buyer_maker`: Whether the buyer was the maker

When loading data, an additional `datetime` column is added, which converts the `time` column to a pandas datetime object.

## Notes

- The default Parquet files location is `/allah/data/trades/eth_usdt_monthly_trades/`
- The files are named in the format `ETHUSDT-trades-YYYY-MM.parquet`
- Some files are very large (several GB), so sampling is recommended for exploratory analysis 
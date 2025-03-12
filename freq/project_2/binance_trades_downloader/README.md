# Binance Trades Downloader

This package provides tools to download and process Binance ETH/USDT trade data.

## Installation

You can install the package directly from the source:

```bash
cd binance_trades_downloader
pip install -e .
```

## Usage

### Command-line Script

After installation, you can use the `download-trades` command:

```bash
# Download all available monthly trade data
download-trades

# Download from a specific start date
download-trades --start_year 2023 --start_month 1
```

### Python Module

```python
from binance_trades_downloader import download_monthly_trades

# Download all available monthly trade data
download_monthly_trades()

# Download from a specific start date
download_monthly_trades(start_year=2023, start_month=1)
```

## Data Structure

The downloaded data is processed and saved in the following format:

- Location: `/allah/data/trades/eth_usdt_monthly_trades/`
- File format: Parquet files named as `ETHUSDT-trades-YYYY-MM.parquet`
- Each file contains the following columns:
  - `id`: Trade ID
  - `price`: Trade price in USDT
  - `qty`: Trade quantity in ETH
  - `quote_qty`: Trade value in USDT (price * qty)
  - `time`: Timestamp in milliseconds
  - `is_buyer_maker`: Whether the buyer was the maker

## Notes

- The script downloads data from Binance's public data repository
- Files are first downloaded as ZIP files, then extracted and converted to Parquet format
- The script checks available disk space before downloading
- Existing files are skipped to avoid re-downloading
- The script shows progress bars and human-readable file sizes 
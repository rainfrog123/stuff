# Binance ETH/USDT Trade Data Tools

This project contains tools for downloading, processing, and analyzing Binance ETH/USDT trade data.

## Sub-projects

### 1. Binance Trades Downloader

A package for downloading and processing Binance ETH/USDT trade data.

```bash
cd binance_trades_downloader
pip install -e .
```

See [binance_trades_downloader/README.md](binance_trades_downloader/README.md) for more details.

### 2. Binance Trade Aggregator

A package for aggregating and analyzing Binance ETH/USDT trade data from Parquet files.

```bash
cd binance_trade_aggregator
pip install -e .
```

See [binance_trade_aggregator/README.md](binance_trade_aggregator/README.md) for more details.

## Workflow

1. Use `binance_trades_downloader` to download and process trade data:
   ```bash
   download-trades
   ```

2. Use `binance_trade_aggregator` to analyze the downloaded data:
   ```bash
   aggregate-trades 2023-01 --end_date 2023-02 --sample_rate 0.01
   ```

## Data Structure

The trade data is stored in Parquet files at `/allah/data/trades/eth_usdt_monthly_trades/` with the following format:
- File naming: `ETHUSDT-trades-YYYY-MM.parquet`
- Columns:
  - `id`: Trade ID
  - `price`: Trade price in USDT
  - `qty`: Trade quantity in ETH
  - `quote_qty`: Trade value in USDT (price * qty)
  - `time`: Timestamp in milliseconds
  - `is_buyer_maker`: Whether the buyer was the maker

## Requirements

- Python 3.11+
- pandas
- pyarrow
- matplotlib
- seaborn
- tqdm
- requests
- humanize 
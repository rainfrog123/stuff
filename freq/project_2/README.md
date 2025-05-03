# Binance Trades Manager

A Python tool for downloading and aggregating Binance ETH/USDT perpetual futures trade data.

## Project Structure

```
project_2/
├── data/                     # Data storage
│   ├── raw/                  # Raw downloaded data
│   ├── processed/            # Processed data files
│   └── labeled_data/         # Labeled datasets for ML
├── scripts/                  # Utility scripts
│   ├── data_collection/      # Data downloading scripts
│   ├── data_processing/      # Data processing & labeling scripts
│   └── analysis/             # Analysis scripts
├── notebooks/                # Jupyter notebooks
├── models/                   # ML model definitions & training
├── indicators/               # Technical indicators
│   └── tv/                   # TradingView indicators
└── user_data/                # FreqTrade user data
```

## Features

- Download monthly ETH/USDT perpetual futures trade data from Binance
- Convert CSV files to Parquet format for efficient storage and faster queries
- Aggregate trade data across multiple months
- Sample data for analysis
- List available data files

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The script provides three main commands:

### 1. Download Trade Data

Download monthly trade data from Binance:

```bash
python scripts/data_collection/binance_trades_monthly.py download [--start_year YEAR] [--start_month MONTH] [--output_dir DIR]
```

Options:
- `--start_year`: Starting year (default: 2019)
- `--start_month`: Starting month (default: 11)
- `--output_dir`: Custom output directory (optional)

Example:
```bash
python scripts/data_collection/binance_trades_monthly.py download --start_year 2022 --start_month 1
```

### 2. Aggregate Trade Data

Load and aggregate trade data for a specific date range:

```bash
python scripts/data_collection/binance_trades_monthly.py aggregate START_DATE [--end_date END_DATE] [--columns COL1 COL2 ...] [--sample_rate RATE] [--output FILE] [--data_dir DIR]
```

Options:
- `START_DATE`: Start date in format YYYY-MM or YYYY-MM-DD
- `--end_date`: End date in format YYYY-MM or YYYY-MM-DD (optional)
- `--columns`: Specific columns to load (optional)
- `--sample_rate`: Sample rate between 0 and 1 (optional)
- `--output`: Output file path (.csv or .parquet) (optional)
- `--data_dir`: Custom data directory (optional)

Example:
```bash
python scripts/data_collection/binance_trades_monthly.py aggregate 2023-01 --end_date 2023-03 --sample_rate 0.1 --output data/processed/trades_sample.parquet
```

### 3. List Available Data

List available data files:

```bash
python scripts/data_collection/binance_trades_monthly.py list [--data_dir DIR]
```

Options:
- `--data_dir`: Custom data directory (optional)

Example:
```bash
python scripts/data_collection/binance_trades_monthly.py list
```

## Data Structure

The downloaded data is stored in Parquet format with the following naming convention:
```
ETHUSDT-trades-YYYY-MM.parquet
```

Each file contains the trade data for a specific month.

## Notes

- The script automatically checks for existing files and only downloads missing data
- Files are downloaded as ZIP, extracted as CSV, and then converted to Parquet format
- The original ZIP and CSV files are deleted after processing to save disk space
- The script checks available disk space before downloading to prevent disk full errors

## License

[MIT License](LICENSE) 
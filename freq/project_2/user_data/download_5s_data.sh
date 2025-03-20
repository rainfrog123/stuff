#!/bin/bash

# Activate the virtual environment
source /allah/freqtrade/.venv/bin/activate

# Change to the freqtrade directory
cd /allah/freqtrade/

# Download 5s data for the pairs in the project
freqtrade download-data \
  --userdir /allah/stuff/freq/project_2/user_data \
  --config /allah/stuff/freq/project_2/user_data/config.json \
  --timerange 20240101- \
  --timeframes 5s 15s 1m \
  --datadir /allah/freqtrade/user_data/data/binance

echo "5-second data download completed!" 
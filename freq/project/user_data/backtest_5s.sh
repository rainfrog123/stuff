#!/bin/bash

# Activate the virtual environment
source /allah/freqtrade/.venv/bin/activate

# Change to the freqtrade directory
cd /allah/freqtrade/

# Run backtesting with 5s timeframe
freqtrade backtesting \
  --strategy TrendReversalLabelingStrategy \
  --userdir /allah/stuff/freq/project_2/user_data \
  --config /allah/stuff/freq/project_2/user_data/config.json \
  --timerange 20240101- \
  --datadir /allah/freqtrade/user_data/data/binance \
  --cache none \
  --starting-balance 10000 \
  --eps \
  --export=signals \
  --fee 0

echo "5-second timeframe backtesting completed!" 
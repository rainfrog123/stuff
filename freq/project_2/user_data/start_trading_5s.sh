#!/bin/bash

# Activate the virtual environment
source /allah/freqtrade/.venv/bin/activate

# Change to the freqtrade directory
cd /allah/freqtrade/

# Start trading with 5s timeframe
freqtrade trade \
  --strategy TrendReversalLabelingStrategy_Prod \
  --userdir /allah/stuff/freq/project_2/user_data \
  --config /allah/stuff/freq/project_2/user_data/config_prod.json 

echo "Trading started with 5-second timeframe" 
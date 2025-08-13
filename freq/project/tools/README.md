# Trading Tools Directory

This directory contains organized tools for data management, analysis, and strategy development.

## Directory Structure

### 📊 **data_management/**
Tools for downloading, converting, and managing trading data:
- `daily_trades.py` - Download and manage Binance daily trade data
- `monthly_trades.py` - Download and manage Binance monthly trade data  
- `convert_to_feather.py` - Convert daily trade data to feather format for freqtrade

### 🔍 **analysis/**
Tools for data analysis and validation:
- `data_analyzer.py` - Comprehensive parquet file analysis and visualization

### 🎯 **strategy_tools/**
Tools for trading strategy development and ML data preparation:
- `tema_labeler.py` - TEMA-50 reversal strategy with ATR-based dynamic labeling
- `tema_exporter.py` - Export labeled strategy data in multiple formats

## Quick Usage

```bash
# Download latest daily trade data
python data_management/daily_trades.py

# Analyze parquet files
python analysis/data_analyzer.py --dir /path/to/data

# Generate TEMA strategy labels
python strategy_tools/tema_labeler.py

# Export labeled data
python strategy_tools/tema_exporter.py
```

## Requirements

All tools require Python 3.7+ with standard trading analysis packages:
- pandas, numpy, matplotlib
- requests, tqdm (for downloaders)
- freqtrade environment (for feather conversion)



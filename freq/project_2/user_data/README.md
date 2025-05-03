# 5-Second Candle Trading System for FreqTrade

This system enables FreqTrade to seamlessly work with 5-second candles from Binance by intercepting the normal data flow and providing custom 5s candle data in the background.

## How It Works

1. **Custom Data Provider**: Intercepts FreqTrade's normal data requests and provides 5s candle data
2. **Background Data Fetching**: Automatically fetches trades from Binance and aggregates them into 5s candles
3. **Seamless Integration**: Works with your existing trading strategies - just run with the custom wrapper

## Quick Start

To run FreqTrade with 5-second candle support:

```bash
/allah/freqtrade/.venv/bin/python3 /allah/stuff/freq/project_2/user_data/scripts/run_with_custom_candles.py --prefetch trade
```

This will:
1. Prefetch some initial 5s candle data
2. Start FreqTrade with the custom data provider
3. Run the TrendRevATR_Custom strategy (which is a wrapper around TrendRevATR)

## Advanced Usage

### Custom Command Line Arguments

Pass any standard FreqTrade arguments after your script arguments:

```bash
/allah/freqtrade/.venv/bin/python3 /allah/stuff/freq/project_2/user_data/scripts/run_with_custom_candles.py --prefetch --pairs ETH/USDT:USDT BTC/USDT:USDT trade --dry-run
```

### Use with Any Strategy

To use your own strategy with 5s candles, create a wrapper similar to TrendRevATR_Custom:

```python
from user_data.strategies.YourStrategy import YourStrategy
from user_data.custom_data_provider import CustomFiveSecondProvider

class YourStrategy_Custom(YourStrategy):
    # Same implementation as TrendRevATR_Custom
    # ...
```

Then run with:

```bash
/allah/freqtrade/.venv/bin/python3 /allah/stuff/freq/project_2/user_data/scripts/run_with_custom_candles.py trade --strategy YourStrategy_Custom
```

## Files Overview

- `custom_data_provider.py` - Custom data provider that delivers 5s candle data
- `strategies/TrendRevATR_Custom.py` - Wrapper for TrendRevATR that loads the custom provider
- `scripts/run_with_custom_candles.py` - Launcher script that runs FreqTrade with 5s support
- `scripts/fetch_binance_trades.py` - Script to fetch and aggregate trades into 5s candles

## Troubleshooting

- **No Data Showing**: Make sure you've prefetched data with the `--prefetch` flag
- **API Connection Issues**: Check your Binance API key in the config
- **Errors at Startup**: Check log files for specific error messages 
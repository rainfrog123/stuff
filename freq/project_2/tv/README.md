# Binance ETH Trading Assistant

A command-line interface (CLI) tool for executing smart limit orders on Binance for ETH trading with high leverage.

## Features

- **ETH Perpetual Futures**: Focused on ETH/USDT perpetual futures contract
- **High Leverage**: Default 125x leverage with automatic fallback to 120x or 115x if needed
- **Smart Limit Orders**: Places limit orders at the best price in the orderbook and dynamically adjusts them if the price changes
- **Entry Timeout**: For entry orders, automatically cancels if not filled within 3 candles (15 seconds for 5s timeframe)
- **Single-Key Commands**: Simple, fast commands for trading:
  - `l` - Enter a LONG position
  - `s` - Enter a SHORT position
  - `t` - Terminate (exit) current position
  - `m` - Market exit (emergency)

## Requirements

- Python 3.11
- CCXT library
- Binance account with API keys (already hardcoded)

## Installation

```bash
# Make sure you're using the FreqTrade virtual environment
source /allah/freqtrade/.venv/bin/activate

# Install required dependencies
pip install ccxt
```

## Usage

1. Run the script:
```bash
cd /allah/stuff/freq/project_2/tv
./binance_assistant.py
```

2. Use the following commands:
   - `l` - Enter a LONG position using a limit order
   - `s` - Enter a SHORT position using a limit order
   - `t` - Terminate (exit) the current position using a limit order
   - `m` - Perform an emergency market exit from the current position
   - `status` - Display current trading status and position information
   - `q` - Quit the application

## How It Works

### High Leverage Trading
- Default leverage is set to 125x for maximum return
- If quantity errors occur, the script automatically steps down leverage to 120x or 115x
- Always uses full available balance for maximum position size

### Smart Limit Orders
When you enter a command to go long (`l`), short (`s`), or terminate a position (`t`), the assistant:

1. Gets the best price from the orderbook (lowest ask for buy, highest bid for sell)
2. Places a limit order at that price
3. Continuously monitors the order status and price changes
4. If the price moves, it cancels and replaces the order at the new best price
5. For entry orders, automatically cancels if not filled within 3 candles (15 seconds)

### Emergency Market Exit
The `m` command immediately places a market order to exit your position, useful for emergency situations where immediate execution is more important than getting the best price.

## Logging

The assistant logs all trading activity to:
- Console output
- A log file (`trading_assistant.log`)

These logs include all order placements, fills, cancellations, and errors. 
# Binance Trading Assistant v2

A command-line trading assistant for Binance Futures, allowing for fast entry and exit of leveraged positions.

## Features

- Trade ETH/USDT futures with high leverage (up to 125x)
- Limit order entry with automatic price adjustments for fast execution
- Market order execution for immediate entry/exit
- Position monitoring and management
- Emergency exit function for fast position closure
- Persistent state tracking to handle ongoing positions

## Installation

1. Ensure you have Python 3.10+ installed
2. Clone this repository
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and add your Binance API credentials:

```bash
cp .env.example .env
# Edit .env file with your API keys
```

## Usage

Run the trading assistant:

```bash
python main.py
```

### Available Commands

- `1`: Enter a long position
- `2`: Enter a short position
- `3`: Exit current position using limit orders
- `4`: Exit current position using market orders (faster)
- `5` or `status`: Show current trading status
- `F` or `force close`: Force close any open position regardless of tracking state
- `C` or `clear tracking state`: Reset position tracking if it gets out of sync
- `L` or `leverage`: Change the leverage multiplier
- `!`: Emergency exit (market exit shortcut)
- `0`, `q`, `quit`, or `exit`: Quit the program

### How It Works

1. **Long/Short Entry**: Places limit orders at the best available price, continuously adjusting to ensure fast execution
2. **Exit Positions**: Uses limit orders for better pricing or market orders for immediate execution
3. **Force Close**: Special function that tries multiple approaches to ensure a position is closed

## Security

This tool requires Binance API keys with Futures trading permissions. For security:

1. Create API keys with **only** Futures trading permissions (no withdrawal access)
2. Store your API keys in the `.env` file, not in the code
3. Never share your API keys or `.env` file

## Customization

You can customize the following parameters in the `.env` file:

- `TRADING_SYMBOL`: The trading pair (default: ETHUSDT)
- `DEFAULT_LEVERAGE`: The default leverage multiplier (default: 125)

## Disclaimer

Trading cryptocurrencies with leverage involves significant risk. This tool is provided for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred while using this software. 
#!/usr/bin/env python3
"""
Launcher script for running FreqTrade with 5-second candle support.
This script wraps the standard FreqTrade startup to inject our custom data provider.
"""
import os
import sys
import logging
import argparse
import importlib.util
from pathlib import Path
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Constants
FREQTRADE_PATH = "/allah/freqtrade"
PYTHON_ENV = "/allah/freqtrade/.venv/bin/python3"
PROJECT_PATH = "/allah/stuff/freq/project_2"
USER_DATA_PATH = f"{PROJECT_PATH}/user_data"
DEFAULT_CONFIG = f"{USER_DATA_PATH}/config_prod.json"
DEFAULT_STRATEGY = "TrendRevATR_Custom"


def setup_path():
    """Add necessary paths to sys.path."""
    # Add freqtrade to path
    sys.path.insert(0, FREQTRADE_PATH)
    # Add project path to path
    sys.path.insert(0, PROJECT_PATH)


def preload_custom_files():
    """
    Preload our custom files to ensure they're available when FreqTrade starts.
    """
    try:
        # Import our custom data provider and strategy
        from user_data.custom_data_provider import CustomFiveSecondProvider
        from user_data.strategies.TrendRevATR_Custom import TrendRevATR_Custom
        
        logger.info("Successfully preloaded custom modules")
        return True
    except Exception as e:
        logger.error(f"Error preloading custom modules: {str(e)}")
        return False


def run_freqtrade(args):
    """
    Run FreqTrade with the provided arguments.
    """
    # Ensure we're using our custom strategy
    if not any(arg.startswith('--strategy') for arg in args):
        args.extend(['--strategy', DEFAULT_STRATEGY])
    
    # Ensure we're using the right config
    if not any(arg.startswith('--config') for arg in args):
        args.extend(['--config', DEFAULT_CONFIG])
    
    # Ensure we're using the right user_data dir
    if not any(arg.startswith('--userdir') for arg in args):
        args.extend(['--userdir', USER_DATA_PATH])
    
    # Build the command
    cmd = [PYTHON_ENV, f"{FREQTRADE_PATH}/freqtrade/main.py"] + args
    
    # Log the command
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run FreqTrade
    try:
        process = subprocess.Popen(cmd)
        process.wait()
        return process.returncode
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping FreqTrade...")
        process.terminate()
        process.wait()
        return 0
    except Exception as e:
        logger.error(f"Error running FreqTrade: {str(e)}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run FreqTrade with 5s candle support')
    parser.add_argument('--prefetch', action='store_true', 
                        help='Prefetch data before starting FreqTrade')
    parser.add_argument('--pairs', type=str, nargs='+', default=["ETH/USDT:USDT"],
                        help='Trading pairs to use (default: ["ETH/USDT:USDT"])')
    parser.add_argument('--days', type=int, default=1,
                        help='Number of days of data to prefetch')
    
    # Split args - first part for this script, rest goes to FreqTrade
    args, ft_args = parser.parse_known_args()
    
    # Setup path
    setup_path()
    
    # Preload custom modules
    if not preload_custom_files():
        logger.error("Failed to preload custom modules, aborting")
        return 1
    
    # Prefetch data if requested
    if args.prefetch:
        logger.info(f"Prefetching data for {args.pairs} (last {args.days} days)")
        fetch_script = f"{USER_DATA_PATH}/scripts/fetch_binance_trades.py"
        fetch_cmd = [
            PYTHON_ENV, fetch_script,
            "--pairs", *args.pairs,
            "--days", str(args.days)
        ]
        try:
            subprocess.run(fetch_cmd, check=True)
            logger.info("Data prefetching completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error prefetching data: {str(e)}")
            return 1
    
    # Run FreqTrade with the custom data provider
    return run_freqtrade(ft_args)


if __name__ == "__main__":
    sys.exit(main()) 
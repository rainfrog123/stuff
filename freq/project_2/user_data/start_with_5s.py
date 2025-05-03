#!/usr/bin/env python3
"""
Custom startup script that applies the 5s timeframe patch
before running Freqtrade
"""
import os
import sys
import importlib.util
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# First, load our patch
logger.info("Loading 5s timeframe patch...")
patch_path = Path(__file__).parent / "strategies" / "timeframe_patch.py"
spec = importlib.util.spec_from_file_location("timeframe_patch", patch_path)
patch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch_module)
logger.info("Patch loaded successfully!")

# Now import the main Freqtrade module
logger.info("Starting Freqtrade...")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from freqtrade.main import main

# Run Freqtrade with our command line arguments
if __name__ == "__main__":
    # Get the arguments that were passed to this script
    args = sys.argv[1:]
    
    # If no arguments provided, use default configuration
    if not args:
        args = [
            "trade",
            "--strategy", "TrendRevATR",
            "--userdir", "/allah/stuff/freq/project_2/user_data",
            "--config", "/allah/stuff/freq/project_2/user_data/config_prod.json"
        ]
    
    # Make sure we have the userdir set correctly
    if "--userdir" not in " ".join(args):
        args.extend(["--userdir", "/allah/stuff/freq/project_2/user_data"])
    
    # Run Freqtrade with our arguments
    sys.argv = [sys.argv[0]] + args
    main() 
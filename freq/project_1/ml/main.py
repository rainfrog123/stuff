# Imports
from data_module import CryptoDataModule
from model import CryptoPricePredictor
from optimization import CryptoOptimizer
from visualization import save_study_results
import pandas as pd
import signal
import sys
from config import (
    DATA_DIR, FEATURES_FILE, BATCH_SIZE, NUM_WORKERS,
    setup_directories
)

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    print("\nReceived interrupt signal. Exiting...")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Setup project directories
        dirs = setup_directories()
        
        # Initialize data module
        data_module = CryptoDataModule(
            directory_path=DATA_DIR,
            batch_size=BATCH_SIZE,
            num_workers=NUM_WORKERS
        )
        
        # Create optimizer
        optimizer = CryptoOptimizer(
            data_module=data_module,
            model_class=CryptoPricePredictor,
            checkpoint_dir=dirs['checkpoint'],
            tensorboard_dir=dirs['tensorboard']
        )
        
        # Run optimization
        study = optimizer.optimize()
        
        # Save results
        if study and study.trials:
            save_study_results(study, dirs['results'])
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
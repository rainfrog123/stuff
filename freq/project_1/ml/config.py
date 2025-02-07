import os

# Data paths
DATA_DIR = '/allah/data/parquet'
FEATURES_FILE = 'ETH/USDT:USDT_raw_features_20250206_184554.parquet'
LABELS_FILE = 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet'

# Training settings
BATCH_SIZE = 64
NUM_WORKERS = 4
MAX_EPOCHS = 50

# Model hyperparameters
HIDDEN_DIM = 128
LEARNING_RATE = 1e-3
DROPOUT = 0.2

# Optimization settings
N_TRIALS = 100
FEATURE_RANGE = (100, 500)
HIDDEN_DIM_RANGE = (64, 512)
LEARNING_RATE_RANGE = (1e-5, 1e-2)
DROPOUT_RANGE = (0.1, 0.5)
BATCH_SIZES = [32, 64, 128, 256]

# Directory settings
def setup_directories():
    """Setup and return project directories."""
    base_dir = os.getcwd()
    dirs = {
        'checkpoint': os.path.join(base_dir, 'checkpoints'),
        'tensorboard': os.path.join(base_dir, 'lightning_logs'),
        'results': os.path.join(base_dir, 'results')
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        
    return dirs 
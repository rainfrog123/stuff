import os

# Data paths
DATA_DIR = '/allah/data/parquet'
FEATURES_FILE = 'ETH/USDT:USDT_raw_features_20250206_184554.parquet'
LABELS_FILE = 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet'

# Training settings
BATCH_SIZE = 64
NUM_WORKERS = 4
MAX_EPOCHS = 50

# Model settings
HIDDEN_DIM = 128
LEARNING_RATE = 1e-3
DROPOUT = 0.2

# Create necessary directories
os.makedirs('checkpoints', exist_ok=True)
os.makedirs('lightning_logs', exist_ok=True)

# Directory settings
def setup_directories():
    """Setup and return project directories."""
    base_dir = os.getcwd()
    dirs = {
        'checkpoint': os.path.join(base_dir, 'checkpoints'),
        'tensorboard': os.path.join(base_dir, 'lightning_logs'),
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        
    return dirs 
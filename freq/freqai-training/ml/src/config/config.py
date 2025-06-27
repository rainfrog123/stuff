from pathlib import Path
from .base_config import BaseConfig

class Config(BaseConfig):
    """Project-specific configuration."""
    
    def __init__(self):
        super().__init__(
            # Data settings
            data_dir=Path('/allah/data/parquet'),
            features_file='ETH/USDT:USDT_raw_features_20250206_184554.parquet',
            labels_file='ETH/USDT:USDT_raw_labels_20250206_184554.parquet',
            
            # Training settings - using defaults from BaseConfig
            batch_size=64,
            num_workers=4,
            max_epochs=50,
            
            # Model settings - using defaults from BaseConfig
            hidden_dim=128,
            learning_rate=1e-3,
            dropout=0.2
        )
        
        # Validate configuration
        self.validate() 
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class BaseConfig:
    """Base configuration class with common settings."""
    
    # Data settings
    data_dir: Path
    features_file: str
    labels_file: str
    
    # Training settings
    batch_size: int = 64
    num_workers: int = 4
    max_epochs: int = 50
    
    # Model settings
    hidden_dim: int = 128
    learning_rate: float = 1e-3
    dropout: float = 0.2
    
    # Paths
    checkpoint_dir: Optional[Path] = None
    tensorboard_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Validate and process configuration after initialization."""
        # Convert string paths to Path objects
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        
        # Set up default directories if not provided
        base_dir = Path.cwd()
        if self.checkpoint_dir is None:
            self.checkpoint_dir = base_dir / 'checkpoints'
        if self.tensorboard_dir is None:
            self.tensorboard_dir = base_dir / 'lightning_logs'
            
        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.tensorboard_dir.mkdir(parents=True, exist_ok=True)
        
    def validate(self):
        """Validate the configuration."""
        # Validate paths
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")
            
        features_path = self.data_dir / self.features_file
        labels_path = self.data_dir / self.labels_file
        
        if not features_path.exists():
            raise ValueError(f"Features file does not exist: {features_path}")
        if not labels_path.exists():
            raise ValueError(f"Labels file does not exist: {labels_path}")
            
        # Validate training parameters
        if self.batch_size < 1:
            raise ValueError(f"Invalid batch size: {self.batch_size}")
        if self.num_workers < 0:
            raise ValueError(f"Invalid number of workers: {self.num_workers}")
        if self.max_epochs < 1:
            raise ValueError(f"Invalid number of epochs: {self.max_epochs}")
            
        # Validate model parameters
        if self.hidden_dim < 1:
            raise ValueError(f"Invalid hidden dimension: {self.hidden_dim}")
        if not 0 < self.learning_rate < 1:
            raise ValueError(f"Invalid learning rate: {self.learning_rate}")
        if not 0 <= self.dropout < 1:
            raise ValueError(f"Invalid dropout rate: {self.dropout}") 
from abc import ABC, abstractmethod
from pathlib import Path
import pytorch_lightning as pl
from torch.utils.data import DataLoader, Dataset
from typing import Optional, Tuple, List
import numpy as np

class BaseDataModule(pl.LightningDataModule, ABC):
    """Base data module with common functionality."""
    
    def __init__(self, batch_size: int = 64, num_workers: int = 4):
        """Initialize the data module.
        
        Args:
            batch_size: Batch size for training
            num_workers: Number of workers for data loading
        """
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        
        # Initialize datasets
        self.train_dataset: Optional[Dataset] = None
        self.val_dataset: Optional[Dataset] = None
        self.test_dataset: Optional[Dataset] = None
        
    def _create_dataloader(self, dataset: Dataset, shuffle: bool = False) -> DataLoader:
        """Create a data loader.
        
        Args:
            dataset: Dataset to create loader for
            shuffle: Whether to shuffle the data
            
        Returns:
            DataLoader instance
        """
        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=shuffle,
            num_workers=self.num_workers,
            pin_memory=True
        )
        
    def train_dataloader(self) -> DataLoader:
        """Get training data loader."""
        if self.train_dataset is None:
            raise RuntimeError("Training dataset not initialized. Call setup() first.")
        return self._create_dataloader(self.train_dataset, shuffle=True)
        
    def val_dataloader(self) -> DataLoader:
        """Get validation data loader."""
        if self.val_dataset is None:
            raise RuntimeError("Validation dataset not initialized. Call setup() first.")
        return self._create_dataloader(self.val_dataset, shuffle=False)
        
    def test_dataloader(self) -> DataLoader:
        """Get test data loader."""
        if self.test_dataset is None:
            raise RuntimeError("Test dataset not initialized. Call setup() first.")
        return self._create_dataloader(self.test_dataset, shuffle=False)
        
    @abstractmethod
    def prepare_data(self) -> None:
        """Prepare data (download, process, etc.)."""
        pass
        
    @abstractmethod
    def setup(self, stage: Optional[str] = None) -> None:
        """Set up datasets for training/validation/testing."""
        pass
        
    def _split_data(self, data: np.ndarray, split_ratios: List[float]) -> List[np.ndarray]:
        """Split data into multiple parts according to ratios.
        
        Args:
            data: Data to split
            split_ratios: List of ratios (should sum to 1)
            
        Returns:
            List of split data arrays
        """
        if abs(sum(split_ratios) - 1.0) > 1e-6:
            raise ValueError("Split ratios must sum to 1")
            
        total_size = len(data)
        splits = []
        start_idx = 0
        
        for ratio in split_ratios[:-1]:  # All but the last ratio
            split_size = int(total_size * ratio)
            splits.append(data[start_idx:start_idx + split_size])
            start_idx += split_size
            
        # Add the remaining data to the last split
        splits.append(data[start_idx:])
        
        return splits 
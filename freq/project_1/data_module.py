import os
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import pytorch_lightning as pl
from typing import Optional, Tuple

class CryptoDataset(Dataset):
    def __init__(self, features: torch.Tensor, labels: torch.Tensor):
        """Initialize dataset with pre-processed tensors for better efficiency."""
        self.features = features
        self.labels = labels

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]

class CryptoDataModule(pl.LightningDataModule):
    def __init__(
        self, 
        directory_path: str, 
        batch_size: int = 128, 
        num_workers: int = 4, 
        train_split: float = 0.8, 
        n_features: int = 20,
        random_seed: int = 42
    ):
        super().__init__()
        self.directory_path = Path(directory_path)
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.train_split = train_split
        self.n_features = n_features
        self.random_seed = random_seed
        self.scaler = StandardScaler()
        self.selected_features = None
        self.input_dim = None
        self.output_dim = None
        
    def prepare_data(self) -> None:
        """Verify data files exist."""
        features_path = self.directory_path / 'ETH/USDT:USDT_raw_features_20250206_184554.parquet'
        labels_path = self.directory_path / 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet'
        
        if not (features_path.exists() and labels_path.exists()):
            raise FileNotFoundError(f"Data files not found in {self.directory_path}/ETH/")
    
    def setup(self, stage: Optional[str] = None) -> None:
        """Setup data with efficient preprocessing."""
        features = pd.read_parquet(self.directory_path / 'ETH/USDT:USDT_raw_features_20250206_184554.parquet')
        labels = pd.read_parquet(self.directory_path / 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet')
        
        print(f"Original features shape: {features.shape}")
        
        np.random.seed(self.random_seed)
        self.selected_features = np.random.choice(features.columns, size=self.n_features, replace=False)
        features = features[self.selected_features]
        
        print(f"\nRandomly selected {self.n_features} features:")
        print(self.selected_features.tolist())
        
        features = features.fillna(0).values
        features = self.scaler.fit_transform(features)
        labels = LabelEncoder().fit_transform(labels['&-target'].values)
        
        features_tensor = torch.tensor(features, dtype=torch.float32)
        labels_tensor = torch.tensor(labels, dtype=torch.long)
        
        dataset = CryptoDataset(features_tensor, labels_tensor)
        
        train_size = int(self.train_split * len(dataset))
        val_size = len(dataset) - train_size
        
        self.train_dataset, self.val_dataset = random_split(
            dataset, 
            [train_size, val_size],
            generator=torch.Generator().manual_seed(self.random_seed)
        )
        
        self.input_dim = self.n_features
        self.output_dim = len(np.unique(labels))
        
        print(f"\nDataset splits:")
        print(f"Training set size: {train_size}")
        print(f"Validation set size: {val_size}")
        print(f"Input dimensions: {self.input_dim}")
        print(f"Output dimensions: {self.output_dim}")

    def train_dataloader(self) -> DataLoader:
        return DataLoader(
            self.train_dataset, 
            batch_size=self.batch_size,
            num_workers=self.num_workers, 
            shuffle=True,
            pin_memory=True,
            drop_last=True,
            persistent_workers=True if self.num_workers > 0 else False
        )

    def val_dataloader(self) -> DataLoader:
        return DataLoader(
            self.val_dataset, 
            batch_size=self.batch_size,
            num_workers=self.num_workers, 
            pin_memory=True,
            drop_last=True,
            persistent_workers=True if self.num_workers > 0 else False
        ) 
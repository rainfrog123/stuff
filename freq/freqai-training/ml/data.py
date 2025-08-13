import os
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl
from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np

class CryptoDataset(Dataset):
    def __init__(self, features, targets):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.long).squeeze()

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]

class CryptoDataModule(pl.LightningDataModule):
    def __init__(self, data_dir, features_file, labels_file, batch_size=64, num_workers=4):
        super().__init__()
        self.data_dir = data_dir
        self.features_file = features_file
        self.labels_file = labels_file
        self.batch_size = batch_size
        self.num_workers = num_workers
        
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.input_dim = None

    def prepare_data(self):
        # Load data
        features_path = os.path.join(self.data_dir, self.features_file)
        labels_path = os.path.join(self.data_dir, self.labels_file)
        
        self._features = pd.read_parquet(features_path)
        self._labels = pd.read_parquet(labels_path)
        
        if len(self._features) != len(self._labels):
            raise ValueError("Features and labels have different lengths")

    def setup(self, stage=None):
        # Preprocess features
        features = self.scaler.fit_transform(self._features)
        targets = self.label_encoder.fit_transform(self._labels['&-target']).reshape(-1, 1)
        
        # Store input dimension
        self.input_dim = features.shape[1]
        
        # Split data
        train_size = int(0.7 * len(features))
        val_size = int(0.15 * len(features))
        
        if stage in (None, 'fit'):
            self.train_dataset = CryptoDataset(
                features[:train_size],
                targets[:train_size]
            )
            self.val_dataset = CryptoDataset(
                features[train_size:train_size + val_size],
                targets[train_size:train_size + val_size]
            )
            
        if stage in (None, 'test'):
            self.test_dataset = CryptoDataset(
                features[train_size + val_size:],
                targets[train_size + val_size:]
            )
        
        # Clear memory
        del features, targets
        self._features = self._labels = None

    def train_dataloader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size, 
                        shuffle=True, num_workers=self.num_workers, pin_memory=True)

    def val_dataloader(self):
        return DataLoader(self.val_dataset, batch_size=self.batch_size,
                        shuffle=False, num_workers=self.num_workers, pin_memory=True)

    def test_dataloader(self):
        return DataLoader(self.test_dataset, batch_size=self.batch_size,
                        shuffle=False, num_workers=self.num_workers, pin_memory=True) 
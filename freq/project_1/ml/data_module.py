import os
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from pytorch_lightning import LightningDataModule
from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np

class CryptoDataset(Dataset):
    def __init__(self, features, targets):
        self.features = torch.FloatTensor(features)
        self.targets = torch.LongTensor(targets)  # Changed to LongTensor for classification

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]

class CryptoDataModule(LightningDataModule):
    def __init__(self, directory_path, batch_size=64, num_workers=4, feature_indices=None):
        super().__init__()
        self.directory_path = directory_path
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.feature_indices = feature_indices
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.input_dim = None  # Will be updated after data loading
        self.num_classes = None  # Will be updated after data loading

    def prepare_data(self):
        # Verify data files exist
        features_path = os.path.join(self.directory_path, 'ETH/USDT:USDT_raw_features_20250206_184554.parquet')
        labels_path = os.path.join(self.directory_path, 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet')
        
        if not (os.path.exists(features_path) and os.path.exists(labels_path)):
            raise FileNotFoundError(f"Data files not found in {self.directory_path}/ETH/")

    def setup(self, stage=None):
        # Load data
        features = pd.read_parquet(os.path.join(self.directory_path, 'ETH/USDT:USDT_raw_features_20250206_184554.parquet'))
        labels = pd.read_parquet(os.path.join(self.directory_path, 'ETH/USDT:USDT_raw_labels_20250206_184554.parquet'))
        
        print(f"Original features shape: {features.shape}")
        
        # Select features if indices are provided
        if self.feature_indices is not None:
            features = features.iloc[:, self.feature_indices]
        
        # Separate features and target
        features = features.fillna(0).values  # Convert to numpy array
        
        # Convert categorical target values to numeric using LabelEncoder
        targets = self.label_encoder.fit_transform(labels['&-target'])
        targets = targets.reshape(-1, 1)
        
        # Store number of classes
        self.num_classes = len(self.label_encoder.classes_)
        print(f"Target classes: {self.label_encoder.classes_}")

        # Scale features
        features = self.scaler.fit_transform(features)

        # Split data
        train_size = int(0.7 * len(features))
        val_size = int(0.15 * len(features))

        self.train_features = features[:train_size]
        self.train_targets = targets[:train_size]
        
        self.val_features = features[train_size:train_size + val_size]
        self.val_targets = targets[train_size:train_size + val_size]
        
        self.test_features = features[train_size + val_size:]
        self.test_targets = targets[train_size + val_size:]

        # Update input dimension based on actual data
        self.input_dim = self.train_features.shape[1]
        
        # Print setup info
        print(f"\nDataset splits:")
        print(f"Training set size: {train_size}")
        print(f"Validation set size: {val_size}")
        print(f"Test set size: {len(self.test_features)}")
        print(f"Input dimensions: {self.input_dim}")
        print(f"Number of classes: {self.num_classes}")

    def train_dataloader(self):
        train_dataset = CryptoDataset(self.train_features, self.train_targets)
        return DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers
        )

    def val_dataloader(self):
        val_dataset = CryptoDataset(self.val_features, self.val_targets)
        return DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers
        )

    def test_dataloader(self):
        test_dataset = CryptoDataset(self.test_features, self.test_targets)
        return DataLoader(
            test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers
        ) 
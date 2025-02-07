import os
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from pytorch_lightning import LightningDataModule
from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np
from config import FEATURES_FILE, LABELS_FILE

class CryptoDataset(Dataset):
    def __init__(self, features, targets):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.long).squeeze()

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]

class CryptoDataModule(LightningDataModule):
    def __init__(self, directory_path, batch_size=64, num_workers=4, feature_indices=None, features_data=None):
        super().__init__()
        self.directory_path = directory_path
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.feature_indices = feature_indices
        self._features_data = None
        self._labels_data = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.input_dim = None
        self.num_classes = None
        
        # Store the features data if provided
        if features_data is not None:
            if not isinstance(features_data, pd.DataFrame):
                raise ValueError("features_data must be a pandas DataFrame")
            self._features_data = features_data.copy()

    def prepare_data(self):
        """Verify data files exist and are valid."""
        features_path = os.path.join(self.directory_path, FEATURES_FILE)
        labels_path = os.path.join(self.directory_path, LABELS_FILE)
        
        # Check if files exist
        if not os.path.exists(features_path):
            raise FileNotFoundError(f"Features file not found: {features_path}")
        if not os.path.exists(labels_path):
            raise FileNotFoundError(f"Labels file not found: {labels_path}")
            
        # Verify files can be read
        try:
            pd.read_parquet(features_path)
            pd.read_parquet(labels_path)
        except Exception as e:
            raise ValueError(f"Error reading data files: {str(e)}")

    def _load_data(self):
        """Load data if not already loaded."""
        try:
            if self._features_data is None:
                features_path = os.path.join(self.directory_path, FEATURES_FILE)
                self._features_data = pd.read_parquet(features_path)
                if self._features_data.empty:
                    raise ValueError("Features data is empty")
                    
            if self._labels_data is None:
                labels_path = os.path.join(self.directory_path, LABELS_FILE)
                self._labels_data = pd.read_parquet(labels_path)
                if self._labels_data.empty:
                    raise ValueError("Labels data is empty")
                    
            # Verify data alignment
            if len(self._features_data) != len(self._labels_data):
                raise ValueError("Features and labels have different lengths")
                
        except Exception as e:
            self._features_data = None
            self._labels_data = None
            raise RuntimeError(f"Failed to load data: {str(e)}")

    def _preprocess_features(self, features):
        """Preprocess features by handling NaN values and scaling."""
        if features is None:
            raise ValueError("Features data is None")
            
        if not isinstance(features, np.ndarray):
            features = features.values
            
        # Replace NaN values with 0
        features = np.nan_to_num(features)
        
        # Scale the features
        features = self.scaler.fit_transform(features)
        return features

    def setup(self, stage=None):
        """Setup data for training, validation, and test."""
        # Load data if not already loaded
        self._load_data()
        
        if self._features_data is None:
            raise RuntimeError("Features data not loaded")
            
        # Get features
        if self.feature_indices is not None:
            if max(self.feature_indices) >= self._features_data.shape[1]:
                raise ValueError("Feature indices out of bounds")
            features = self._features_data.iloc[:, self.feature_indices].values
        else:
            features = self._features_data.values
            
        print(f"Original features shape: {features.shape}")
        
        # Preprocess features
        features = self._preprocess_features(features)
        
        # Process labels
        targets = self.label_encoder.fit_transform(self._labels_data['&-target'])
        targets = targets.reshape(-1, 1)
        
        # Store number of classes
        self.num_classes = len(self.label_encoder.classes_)
        print(f"Target classes: {self.label_encoder.classes_}")

        # Split data efficiently
        total_samples = len(features)
        train_size = int(0.7 * total_samples)
        val_size = int(0.15 * total_samples)
        
        # Create datasets
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

        # Update input dimension based on actual data
        self.input_dim = features.shape[1]
        
        # Print setup info
        print(f"\nDataset splits:")
        print(f"Training set size: {train_size}")
        print(f"Validation set size: {val_size}")
        print(f"Test set size: {total_samples - train_size - val_size}")
        print(f"Input dimensions: {self.input_dim}")
        print(f"Number of classes: {self.num_classes}")
        
        # Clear memory
        del features, targets
        if stage == 'fit':
            del self._features_data
            del self._labels_data

    def train_dataloader(self):
        if self.train_dataset is None:
            raise RuntimeError("Training dataset not initialized. Call setup() first.")
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=True
        )

    def val_dataloader(self):
        if self.val_dataset is None:
            raise RuntimeError("Validation dataset not initialized. Call setup() first.")
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True
        )

    def test_dataloader(self):
        if self.test_dataset is None:
            raise RuntimeError("Test dataset not initialized. Call setup() first.")
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True
        ) 
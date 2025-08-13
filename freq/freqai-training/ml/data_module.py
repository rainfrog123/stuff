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
    def __init__(self, directory_path, batch_size=64, num_workers=4):
        super().__init__()
        self.directory_path = directory_path
        self.batch_size = batch_size
        self.num_workers = num_workers
        
        # Initialize data holders
        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.input_dim = None
        self.num_classes = None

    def prepare_data(self):
        """Load and prepare the data."""
        try:
            # Load feature data
            features_path = os.path.join(self.directory_path, FEATURES_FILE)
            if not os.path.exists(features_path):
                raise FileNotFoundError(f"Features file not found: {features_path}")
            self._features_data = pd.read_parquet(features_path)
            if self._features_data.empty:
                raise ValueError("Features data is empty")
            
            # Load label data
            labels_path = os.path.join(self.directory_path, LABELS_FILE)
            if not os.path.exists(labels_path):
                raise FileNotFoundError(f"Labels file not found: {labels_path}")
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
        if self._features_data is None or self._labels_data is None:
            raise RuntimeError("Data not loaded. Call prepare_data() first.")
            
        # Get and preprocess features
        features = self._preprocess_features(self._features_data)
        
        # Process labels
        targets = self.label_encoder.fit_transform(self._labels_data['&-target'])
        targets = targets.reshape(-1, 1)
        
        # Store number of classes and input dimensions
        self.num_classes = len(self.label_encoder.classes_)
        self.input_dim = features.shape[1]
        
        # Print data info
        print(f"\nData Information:")
        print(f"Total samples: {len(features)}")
        print(f"Input dimensions: {self.input_dim}")
        print(f"Number of classes: {self.num_classes}")
        print(f"Target classes: {self.label_encoder.classes_}")

        # Split data
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
            
            print(f"\nDataset splits:")
            print(f"Training set size: {len(self.train_dataset)}")
            print(f"Validation set size: {len(self.val_dataset)}")
            
        if stage in (None, 'test'):
            self.test_dataset = CryptoDataset(
                features[train_size + val_size:],
                targets[train_size + val_size:]
            )
            print(f"Test set size: {len(self.test_dataset)}")
        
        # Clear memory
        del features, targets
        self._features_data = None
        self._labels_data = None

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
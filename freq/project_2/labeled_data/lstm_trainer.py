#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LSTM Model Training with PyTorch Lightning
-----------------------------------------
This script loads the preprocessed binary trading data, 
trains an LSTM model using PyTorch Lightning, and logs metrics with TensorBoard.
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import json
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import TensorBoardLogger
from typing import Dict, List, Tuple, Optional, Union
import argparse
import subprocess
import threading
import time
import webbrowser


# Launch TensorBoard
def launch_tensorboard(logdir: str, port: int = 6006, open_browser: bool = True):
    def run_tensorboard():
        cmd = ['/allah/freqtrade/.venv/bin/tensorboard', '--logdir', logdir, '--port', str(port)]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        if open_browser:
            webbrowser.open(f'http://localhost:{port}')
        process.wait()
    
    tb_thread = threading.Thread(target=run_tensorboard, daemon=True)
    tb_thread.start()
    print(f"TensorBoard started at http://localhost:{port}")
    return tb_thread


class LSTMDataModule(pl.LightningDataModule):
    """Lightning DataModule for LSTM trading data"""
    
    def __init__(
        self,
        data_dir: str = "./lstm_data",
        batch_size: int = 64,
        num_workers: int = 4,
        file_prefix: str = "lstm_profit_data",
        val_split: float = 0.2,
        test_split: float = 0.1
    ):
        super().__init__()
        self.data_dir = data_dir
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.file_prefix = file_prefix
        self.val_split = val_split
        self.test_split = test_split
        
        self.train_idx = None
        self.val_idx = None
        self.test_idx = None
        
        self.X = None
        self.y = None
        self.features = None
    
    def prepare_data(self):
        pass
    
    def setup(self, stage: Optional[str] = None):
        """Load data and set up train/val/test splits"""
        # Load the data
        data_files = os.listdir(self.data_dir)
        print(f"Available files in {self.data_dir}:")
        print(data_files)
        
        X_file = os.path.join(self.data_dir, f"{self.file_prefix}_X.npy")
        y_file = os.path.join(self.data_dir, f"{self.file_prefix}_y.npy")
        
        if not os.path.exists(X_file):
            raise FileNotFoundError(f"X data file not found: {X_file}")
        if not os.path.exists(y_file):
            raise FileNotFoundError(f"y data file not found: {y_file}")
            
        print(f"Loading data from: {X_file} and {y_file}")
        self.X = np.load(X_file)
        self.y = np.load(y_file)
        
        # Map -1 to 0 for PyTorch which expects classes 0 and 1
        self.y = np.where(self.y == -1, 0, self.y)
        
        print(f"Original class distribution before mapping:")
        orig_classes, orig_counts = np.unique(np.load(y_file), return_counts=True)
        print(dict(zip(orig_classes, orig_counts)))
        
        print(f"Mapped class distribution (0=unprofitable, 1=profitable):")
        classes, counts = np.unique(self.y, return_counts=True)
        print(dict(zip(classes, counts)))
        
        # Load feature names
        feature_file = os.path.join(self.data_dir, f"{self.file_prefix}_features.txt")
        if os.path.exists(feature_file):
            with open(feature_file, 'r') as f:
                self.features = [line.strip() for line in f.readlines()]
            print(f"Features: {self.features}")
        else:
            self.features = [f"feature_{i}" for i in range(self.X.shape[2])]
            print(f"Feature file not found, using generic feature names")
        
        # Try to load metadata
        metadata_file = os.path.join(self.data_dir, f"{self.file_prefix}_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                self.metadata = json.load(f)
            print(f"Dataset shape from metadata: X={self.metadata['X_shape']}, y={self.metadata['y_shape']}")
        else:
            self.metadata = {
                "X_shape": self.X.shape,
                "y_shape": self.y.shape,
                "class_distribution": dict(zip(classes.tolist(), counts.tolist()))
            }
            print(f"Metadata file not found, using computed values")
        
        # Print dataset info
        print(f"Actual dataset shape: X={self.X.shape}, y={self.y.shape}")
        
        # Create indices for train/val/test splits
        dataset_size = len(self.X)
        indices = np.random.permutation(dataset_size)
        
        test_size = int(self.test_split * dataset_size)
        val_size = int(self.val_split * dataset_size)
        train_size = dataset_size - test_size - val_size
        
        self.train_idx = indices[:train_size]
        self.val_idx = indices[train_size:train_size + val_size]
        self.test_idx = indices[train_size + val_size:]
        
        print(f"Split sizes - Train: {len(self.train_idx)}, Val: {len(self.val_idx)}, Test: {len(self.test_idx)}")
    
    def train_dataloader(self):
        X_train = torch.FloatTensor(self.X[self.train_idx])
        y_train = torch.LongTensor(self.y[self.train_idx])
        train_dataset = TensorDataset(X_train, y_train)
        
        return DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers
        )
    
    def val_dataloader(self):
        X_val = torch.FloatTensor(self.X[self.val_idx])
        y_val = torch.LongTensor(self.y[self.val_idx])
        val_dataset = TensorDataset(X_val, y_val)
        
        return DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers
        )
    
    def test_dataloader(self):
        X_test = torch.FloatTensor(self.X[self.test_idx])
        y_test = torch.LongTensor(self.y[self.test_idx])
        test_dataset = TensorDataset(X_test, y_test)
        
        return DataLoader(
            test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers
        )


class BasicLSTMModel(pl.LightningModule):
    """Lightning Module for LSTM trading classification"""
    
    def __init__(
        self,
        input_size: int = 3,  # Number of features
        hidden_size: int = 100,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        class_weights: Optional[torch.Tensor] = None
    ):
        super().__init__()
        self.save_hyperparameters()
        
        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=False
        )
        
        # Fully connected layers for classification
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 2)  # Binary classification: 0=unprofitable, 1=profitable
        )
        
        # Loss function with class weighting if provided
        self.class_weights = class_weights
        self.criterion = nn.CrossEntropyLoss(weight=class_weights)
        
        # Initialize weights
        self._init_weights()
        
        # Debug counter
        self.batch_count = 0
    
    def _init_weights(self):
        """Initialize weights to help with training"""
        for name, param in self.named_parameters():
            if 'weight' in name:
                if len(param.shape) > 1:
                    nn.init.xavier_uniform_(param)
                else:
                    nn.init.uniform_(param, -0.1, 0.1)
            elif 'bias' in name:
                nn.init.zeros_(param)
    
    def forward(self, x):
        # x shape: [batch_size, seq_len, features]
        
        # Debug info every 50 batches
        if self.training and self.batch_count % 50 == 0:
            # Print some stats about the input
            print(f"Input stats - Shape: {x.shape}, Min: {x.min().item():.4f}, Max: {x.max().item():.4f}, Mean: {x.mean().item():.4f}")
            
            # Sample a random example to inspect
            sample_idx = np.random.randint(0, x.shape[0])
            sample = x[sample_idx]
            print(f"Sample input - Direction: {sample[0, 0].item():.4f}, RSI: {sample[0, 1].item():.4f}, VWAP: {sample[0, 2].item():.4f}")
        
        lstm_out, _ = self.lstm(x)
        
        # Use only the last output of the LSTM
        last_output = lstm_out[:, -1, :]
        
        # Pass through fully connected layers
        output = self.fc(last_output)
        
        # Debug prediction distribution
        if self.training and self.batch_count % 50 == 0:
            with torch.no_grad():
                probs = torch.softmax(output, dim=1)
                pred_class = torch.argmax(output, dim=1)
                class_counts = torch.bincount(pred_class, minlength=2)
                print(f"Prediction distribution - Class 0: {class_counts[0].item()}, Class 1: {class_counts[1].item()}")
                print(f"Mean probabilities - Class 0: {probs[:, 0].mean().item():.4f}, Class 1: {probs[:, 1].mean().item():.4f}")
        
        self.batch_count += 1
        return output
    
    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        # Calculate metrics for class 1 (profitable)
        y_cpu = y.cpu().numpy()
        preds_cpu = preds.cpu().numpy()
        
        # Make sure to handle edge cases
        if len(np.unique(y_cpu)) > 1:  # Only calculate if we have examples of both classes
            precision = precision_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            recall = recall_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            f1 = f1_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            
            self.log("train_precision", precision, prog_bar=True, on_step=False, on_epoch=True)
            self.log("train_recall", recall, prog_bar=True, on_step=False, on_epoch=True)
            self.log("train_f1", f1, prog_bar=True, on_step=False, on_epoch=True)
        
        self.log("train_loss", loss, prog_bar=True, on_step=True, on_epoch=True)
        self.log("train_acc", acc, prog_bar=True, on_step=False, on_epoch=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        # Calculate metrics for class 1 (profitable)
        y_cpu = y.cpu().numpy()
        preds_cpu = preds.cpu().numpy()
        
        # Only calculate if we have examples of both classes and both in predictions
        if len(np.unique(y_cpu)) > 1:
            precision = precision_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            recall = recall_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            f1 = f1_score(y_cpu, preds_cpu, pos_label=1, zero_division=0)
            
            self.log("val_precision", precision, prog_bar=True, on_step=False, on_epoch=True)
            self.log("val_recall", recall, prog_bar=True, on_step=False, on_epoch=True)
            self.log("val_f1", f1, prog_bar=True, on_step=False, on_epoch=True)
        else:
            self.log("val_precision", 0.0, prog_bar=True, on_step=False, on_epoch=True)
            self.log("val_recall", 0.0, prog_bar=True, on_step=False, on_epoch=True)
            self.log("val_f1", 0.0, prog_bar=True, on_step=False, on_epoch=True)
        
        self.log("val_loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("val_acc", acc, prog_bar=True, on_step=False, on_epoch=True)
        
        return {"val_loss": loss, "val_acc": acc}
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = self.criterion(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        self.log("test_loss", loss)
        self.log("test_acc", acc)
        
        # Store for epoch end processing
        self.test_step_outputs = getattr(self, "test_step_outputs", [])
        self.test_step_outputs.append({
            "preds": preds,
            "targets": y
        })
        
        return {"test_loss": loss, "test_acc": acc}
    
    def on_test_epoch_end(self):
        outputs = self.test_step_outputs
        
        # Concatenate all predictions and targets
        all_preds = torch.cat([x["preds"] for x in outputs]).cpu().numpy()
        all_targets = torch.cat([x["targets"] for x in outputs]).cpu().numpy()
        
        # Calculate metrics
        accuracy = accuracy_score(all_targets, all_preds)
        
        if len(np.unique(all_preds)) > 1 and len(np.unique(all_targets)) > 1:
            precision = precision_score(all_targets, all_preds, pos_label=1, zero_division=0)
            recall = recall_score(all_targets, all_preds, pos_label=1, zero_division=0)
            f1 = f1_score(all_targets, all_preds, pos_label=1, zero_division=0)
        else:
            precision, recall, f1 = 0, 0, 0
        
        metrics = {
            "test_accuracy": accuracy,
            "test_precision": precision,
            "test_recall": recall,
            "test_f1": f1
        }
        
        self.log_dict(metrics)
        
        # Print metrics
        print("\nTest Results:")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Precision (Class 1 - Profitable): {precision:.4f}")
        print(f"Recall (Class 1 - Profitable): {recall:.4f}")
        print(f"F1 Score (Class 1 - Profitable): {f1:.4f}")
        
        # Create and log confusion matrix
        cm = confusion_matrix(all_targets, all_preds)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Unprofitable', 'Profitable'],
                   yticklabels=['Unprofitable', 'Profitable'])
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.title('Confusion Matrix')
        plt.tight_layout()
        
        # Save confusion matrix to file
        os.makedirs('results', exist_ok=True)
        plt.savefig('results/confusion_matrix.png')
        
        # Clear saved outputs
        self.test_step_outputs = []
        
        return metrics
    
    def configure_optimizers(self):
        optimizer = optim.Adam(
            self.parameters(),
            lr=self.hparams.learning_rate
        )
        
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "interval": "epoch",
                "frequency": 1
            }
        }


def train_model(
    data_dir: str = "./lstm_data",
    batch_size: int = 32,
    max_epochs: int = 50,
    learning_rate: float = 0.001,
    hidden_size: int = 100,
    num_layers: int = 2,
    dropout: float = 0.3,
    file_prefix: str = "lstm_profit_data",
    class_weight_ratio: float = 1.0  # 1.0 means balanced
):
    """Main training function"""
    # Set up data module
    dm = LSTMDataModule(
        data_dir=data_dir,
        batch_size=batch_size,
        file_prefix=file_prefix
    )
    dm.setup()
    
    # Input size from data
    input_size = dm.X.shape[2]
    
    # Set up class weights
    class_weights = None
    if class_weight_ratio != 1.0:
        weights = torch.FloatTensor([class_weight_ratio, 1.0])
        weights = weights / weights.sum()
        class_weights = weights
        print(f"Using class weights: {weights}")
    
    # Create model
    model = BasicLSTMModel(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
        learning_rate=learning_rate,
        class_weights=class_weights
    )
    
    # Set up callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath="checkpoints",
        filename="lstm-{epoch:02d}-{val_f1:.4f}",
        save_top_k=3,
        monitor="val_f1",
        mode="max"
    )
    
    early_stopping = EarlyStopping(
        monitor="val_f1",
        patience=10,
        mode="max",
        verbose=True
    )
    
    # Set up logger
    logger = TensorBoardLogger("logs", name="lstm_trading")
    
    # Train model
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="cpu",
        devices=1,
        callbacks=[checkpoint_callback, early_stopping],
        logger=logger,
        log_every_n_steps=10
    )
    
    trainer.fit(model, dm)
    
    # Test model
    trainer.test(model, datamodule=dm)
    
    # Save final model
    os.makedirs("models", exist_ok=True)
    trainer.save_checkpoint("models/lstm_final.ckpt")
    
    return model


def main():
    """Entry point"""
    # Configure data directory and file prefix
    data_dir = "./lstm_data"
    file_prefix = "lstm_profit_data"  # Uses the profit/loss data
    
    # Verify data files exist
    X_file = os.path.join(data_dir, f"{file_prefix}_X.npy")
    y_file = os.path.join(data_dir, f"{file_prefix}_y.npy")
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory {data_dir} does not exist")
        return
    
    files = os.listdir(data_dir)
    print(f"Files in {data_dir}: {files}")
    
    if not os.path.exists(X_file):
        print(f"Error: X data file {X_file} not found")
        # Try finding files with similar names
        npy_files = [f for f in files if f.endswith('.npy') and 'X' in f]
        if npy_files:
            print(f"Found other X files: {npy_files}")
            # Suggest using the first one
            file_prefix = npy_files[0].replace('_X.npy', '')
            print(f"Will try using prefix: {file_prefix}")
        else:
            print("No suitable X data files found")
            return
    
    # Filter features if needed
    filter_features = True
    
    if filter_features:
        # No need to re-import modules that are already imported at the top
        # Load and filter data
        feature_file = os.path.join(data_dir, f"{file_prefix}_features.txt")
        X_file = os.path.join(data_dir, f"{file_prefix}_X.npy")
        y_file = os.path.join(data_dir, f"{file_prefix}_y.npy")
        metadata_file = os.path.join(data_dir, f"{file_prefix}_metadata.json")
        
        # Check if files exist again after possible prefix update
        if not os.path.exists(X_file) or not os.path.exists(y_file):
            print(f"Error: Data files not found even after updating prefix")
            return
        
        X_data = np.load(X_file)
        y_data = np.load(y_file)
        
        print(f"Loaded data shapes - X: {X_data.shape}, y: {y_data.shape}")
        
        if os.path.exists(feature_file):
            with open(feature_file, 'r') as f:
                all_features = [line.strip() for line in f.readlines()]
            
            print(f"Original features: {all_features}")
            
            # Filter to only keep direction, rsi_14, and vwap_60
            keep_features = ['direction', 'rsi_14', 'vwap_60']
            feature_indices = [i for i, feat in enumerate(all_features) if feat in keep_features]
            
            if not feature_indices:
                print(f"Warning: None of the features {keep_features} found in {all_features}")
                print("Using all features instead")
                X_filtered = X_data
                filtered_features = all_features
            else:
                X_filtered = X_data[:, :, feature_indices]
                filtered_features = [all_features[i] for i in feature_indices]
                print(f"Filtered to features: {filtered_features}")
        else:
            print(f"Feature file {feature_file} not found, using all features")
            X_filtered = X_data
            filtered_features = [f"feature_{i}" for i in range(X_data.shape[2])]
        
        print(f"Original X shape: {X_data.shape}, Filtered X shape: {X_filtered.shape}")
        
        # Save filtered data with a new prefix
        filtered_prefix = f"{file_prefix}_filtered"
        filtered_X_file = os.path.join(data_dir, f"{filtered_prefix}_X.npy")
        filtered_y_file = os.path.join(data_dir, f"{filtered_prefix}_y.npy")
        
        np.save(filtered_X_file, X_filtered)
        np.save(filtered_y_file, y_data)
        print(f"Saved filtered data to {filtered_X_file} and {filtered_y_file}")
        
        with open(os.path.join(data_dir, f"{filtered_prefix}_features.txt"), 'w') as f:
            for feat in filtered_features:
                f.write(f"{feat}\n")
        
        # Create or update metadata
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            unique_classes, counts = np.unique(y_data, return_counts=True)
            class_distribution = {str(int(cls)): int(count) for cls, count in zip(unique_classes, counts)}
            metadata = {
                'class_distribution': class_distribution
            }
        
        metadata['X_shape'] = [int(X_filtered.shape[0]), int(X_filtered.shape[1]), int(X_filtered.shape[2])]
        metadata['y_shape'] = [int(y_data.shape[0])]
        metadata['sequence_length'] = int(X_filtered.shape[1])
        metadata['num_features'] = int(X_filtered.shape[2])
        metadata['feature_columns'] = filtered_features
        
        with open(os.path.join(data_dir, f"{filtered_prefix}_metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved filtered metadata to {os.path.join(data_dir, f'{filtered_prefix}_metadata.json')}")
        
        # Update file_prefix to use the filtered data
        file_prefix = filtered_prefix
    
    # Launch TensorBoard
    tb_thread = launch_tensorboard("logs", port=6006)
    
    # Training parameters
    batch_size = 32
    hidden_size = 128
    num_layers = 2
    dropout = 0.2
    learning_rate = 0.001
    max_epochs = 50
    class_weight_ratio = 0.9  # Slightly favor class 1 (profitable)
    
    # Train model
    print("\n" + "="*80)
    print("Starting LSTM training with the following configuration:")
    print(f"File prefix: {file_prefix}")
    print(f"Data files: {os.path.join(data_dir, f'{file_prefix}_X.npy')} and {os.path.join(data_dir, f'{file_prefix}_y.npy')}")
    print(f"Model: {hidden_size} hidden units, {num_layers} layers, {dropout} dropout")
    print(f"Training: batch_size={batch_size}, lr={learning_rate}, epochs={max_epochs}")
    print("="*80 + "\n")
    
    model = train_model(
        data_dir=data_dir,
        batch_size=batch_size,
        max_epochs=max_epochs,
        learning_rate=learning_rate,
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
        file_prefix=file_prefix,
        class_weight_ratio=class_weight_ratio
    )
    
    # Keep TensorBoard running
    try:
        while tb_thread.is_alive():
            print("\nTraining complete. TensorBoard server still running at http://localhost:6006")
            print("Press Ctrl+C to stop.")
            time.sleep(60)
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main() 
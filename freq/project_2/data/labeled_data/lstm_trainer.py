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
        file_prefix: str = "trade_outcome_data",
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
        self.price_data = None
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
        weight_decay: float = 0.0,
        class_weights: Optional[torch.Tensor] = None,
        fc_size: int = 64,
        use_batch_norm: bool = True,
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
        
        # Batch normalization (optional)
        self.use_batch_norm = use_batch_norm
        if use_batch_norm:
            self.batch_norm = nn.BatchNorm1d(hidden_size)
        
        # Fully connected layers for classification
        fc_layers = []
        
        # First layer with optional batch norm
        fc_layers.append(nn.Linear(hidden_size, fc_size))
        fc_layers.append(nn.ReLU())
        fc_layers.append(nn.Dropout(dropout))
        
        # Second layer (output)
        fc_layers.append(nn.Linear(fc_size, 2))  # Binary classification: 0=unprofitable, 1=profitable
        
        self.fc = nn.Sequential(*fc_layers)
        
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
            print(f"Sample input (first 3 features) - {sample[0, 0].item():.4f}, {sample[0, 1].item():.4f}, {sample[0, 2].item():.4f}")
        
        lstm_out, _ = self.lstm(x)
        
        # Use only the last output of the LSTM
        last_output = lstm_out[:, -1, :]
        
        # Apply batch normalization if enabled
        if self.use_batch_norm:
            last_output = self.batch_norm(last_output)
        
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
            lr=self.hparams.learning_rate,
            weight_decay=self.hparams.weight_decay
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
    weight_decay: float = 0.0,
    hidden_size: int = 100,
    num_layers: int = 2,
    dropout: float = 0.3,
    file_prefix: str = "trade_outcome_data",
    class_weight_ratio: float = 1.0,  # 1.0 means balanced
    log_dir: str = "logs",
    fc_size: int = 64,
    use_batch_norm: bool = True
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
        # Weight for unprofitable (0) and profitable (1) classes
        weights = torch.FloatTensor([1.0, class_weight_ratio])
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
        weight_decay=weight_decay,
        class_weights=class_weights,
        fc_size=fc_size,
        use_batch_norm=use_batch_norm
    )
    
    # Set up callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath="checkpoints",
        filename=f"lstm-{file_prefix}-{{epoch:02d}}-{{val_f1:.4f}}",
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
    logger = TensorBoardLogger(log_dir, name=f"lstm_{file_prefix}")
    
    # Train model
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="cpu",  # Use "gpu" if available
        devices=1,
        callbacks=[checkpoint_callback, early_stopping],
        logger=logger,
        log_every_n_steps=10
    )
    
    trainer.fit(model, dm)
    
    # Test model
    results = trainer.test(model, datamodule=dm)
    
    # Extract and format results
    result_dict = {
        "accuracy": results[0]["test_accuracy"],
        "precision": results[0]["test_precision"],
        "recall": results[0]["test_recall"],
        "f1": results[0]["test_f1"]
    }
    
    # Save final model
    os.makedirs("models", exist_ok=True)
    model_path = f"models/lstm_{file_prefix}_final.ckpt"
    trainer.save_checkpoint(model_path)
    print(f"Final model saved to {model_path}")
    
    return model, result_dict


def main():
    """Entry point"""
    # Configure data directory and file prefix
    data_dir = "./lstm_data"
    file_prefix = "trade_outcome_data"  # Uses the trade outcome data
    
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
        npy_files = [f for f in files if f.endswith('.npy') and '_X' in f]
        if npy_files:
            print(f"Found other X files: {npy_files}")
            # Suggest using the first one
            file_prefix = npy_files[0].replace('_X.npy', '')
            print(f"Will try using prefix: {file_prefix}")
            
            # Update file paths with new prefix
            X_file = os.path.join(data_dir, f"{file_prefix}_X.npy")
            y_file = os.path.join(data_dir, f"{file_prefix}_y.npy")
            
            # Double-check that they exist
            if not os.path.exists(X_file) or not os.path.exists(y_file):
                print(f"Error: Data files not found even after updating prefix")
                return
        else:
            print("No suitable X data files found")
            return
    
    # Launch TensorBoard
    tb_thread = launch_tensorboard("logs", port=6006)
    
    # Training parameters
    batch_size = 32
    hidden_size = 128
    num_layers = 2
    dropout = 0.2
    learning_rate = 0.001
    weight_decay = 0.0001  # L2 regularization
    max_epochs = 50
    class_weight_ratio = 2.0  # Higher weight for profitable trades
    
    # Train model
    print("\n" + "="*80)
    print("Starting LSTM training with the following configuration:")
    print(f"File prefix: {file_prefix}")
    print(f"Data files: {os.path.join(data_dir, f'{file_prefix}_X.npy')} and {os.path.join(data_dir, f'{file_prefix}_y.npy')}")
    print(f"Model: {hidden_size} hidden units, {num_layers} layers, {dropout} dropout")
    print(f"Training: batch_size={batch_size}, lr={learning_rate}, weight_decay={weight_decay}, epochs={max_epochs}")
    print(f"Class weight ratio (profitable:unprofitable): {class_weight_ratio}")
    print("="*80 + "\n")
    
    model, results = train_model(
        data_dir=data_dir,
        batch_size=batch_size,
        max_epochs=max_epochs,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
        file_prefix=file_prefix,
        class_weight_ratio=class_weight_ratio
    )
    
    # Print final results
    print("\n" + "="*80)
    print("Training complete! Final results:")
    print(f"Accuracy: {results['accuracy']:.4f}")
    print(f"Precision: {results['precision']:.4f}")
    print(f"Recall: {results['recall']:.4f}")
    print(f"F1 Score: {results['f1']:.4f}")
    print("="*80 + "\n")
    
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
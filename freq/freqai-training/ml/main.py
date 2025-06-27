#!/usr/bin/env python3

import os
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
import pandas as pd
from torchmetrics import Precision, Recall, F1Score
import subprocess

# Start TensorBoard at beginning
subprocess.Popen(['tensorboard', '--logdir=lightning_logs', '--port=6006'])

class CryptoDataset(Dataset):
    def __init__(self, features_path, labels_path):
        self.features = pd.read_parquet(features_path).fillna(0)
        self.labels = pd.read_parquet(labels_path)
        
    def __len__(self): return len(self.features)
    def __getitem__(self, idx): return torch.tensor(self.features.iloc[idx].values, dtype=torch.float32), torch.tensor(self.labels.iloc[idx].values[0], dtype=torch.long)

class CryptoModel(pl.LightningModule):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 2)
        )
        self.metrics = {'precision': Precision(task='binary'), 'recall': Recall(task='binary'), 'f1': F1Score(task='binary')}
    
    def forward(self, x): return self.net(x)
    
    def _step(self, batch, stage):
        x, y = batch
        logits = self(x)
        loss = F.cross_entropy(logits, y)
        self.log(f'{stage}_loss', loss, prog_bar=True)
        probs = F.softmax(logits, dim=1)[:, 1]
        for name, metric in self.metrics.items():
            self.log(f'{stage}_{name}', metric(probs, y), prog_bar=True)
        return loss
    
    training_step = lambda self, batch, _: self._step(batch, 'train')
    validation_step = lambda self, batch, _: self._step(batch, 'val')
    configure_optimizers = lambda self: torch.optim.Adam(self.parameters(), lr=1e-3)

def main():
    # Data setup
    data = CryptoDataset(
        '/allah/data/parquet/ETH/USDT:USDT_raw_features_20250206_184554.parquet',
        '/allah/data/parquet/ETH/USDT:USDT_raw_labels_20250206_184554.parquet'
    )
    train_size = int(0.8 * len(data))
    train_data, val_data = torch.utils.data.random_split(data, [train_size, len(data) - train_size])
    train_loader = DataLoader(train_data, batch_size=32, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_data, batch_size=32, num_workers=4)
    
    # Model and training setup
    model = CryptoModel(input_dim=len(data.features.columns))
    trainer = pl.Trainer(
        max_epochs=100,
        callbacks=[
            ModelCheckpoint(dirpath='checkpoints', filename='best-{val_loss:.3f}', monitor='val_loss', mode='min'),
            EarlyStopping(monitor='val_loss', patience=15),
            LearningRateMonitor(logging_interval='epoch')
        ],
        logger=TensorBoardLogger("lightning_logs", name="crypto_predictor"),
        accelerator='auto',
        devices=1
    )
    
    trainer.fit(model, train_loader, val_loader)

if __name__ == "__main__": main()
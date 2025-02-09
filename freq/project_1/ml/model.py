import pytorch_lightning as pl
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchmetrics import Precision, Recall, F1Score
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
import os

class CryptoPricePredictor(pl.LightningModule):
    def __init__(self, input_dim, hidden_dim=128, learning_rate=1e-3, dropout=0.2):
        super().__init__()
        self.save_hyperparameters()
        
        # Network layers
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.layer3 = nn.Linear(hidden_dim, 2)  # Binary classification
        self.dropout = nn.Dropout(dropout)
        
        # Metrics
        metrics = lambda: {'precision': Precision(task='binary'),
                         'recall': Recall(task='binary'),
                         'f1': F1Score(task='binary')}
        self.train_metrics = metrics()
        self.val_metrics = metrics()
        self.test_metrics = metrics()

    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = self.dropout(x)
        x = F.relu(self.layer2(x))
        x = self.dropout(x)
        return self.layer3(x)
    
    def _step(self, batch, metrics, prefix):
        x, y = batch
        y = y.squeeze()
        logits = self(x)
        loss = F.cross_entropy(logits, y)
        
        # Log metrics
        self.log(f'{prefix}_loss', loss, prog_bar=True)
        probs = F.softmax(logits, dim=1)[:, 1]
        
        for name, metric in metrics.items():
            value = metric(probs, y)
            self.log(f'{prefix}_{name}', value, prog_bar=True)
        
        return loss

    def training_step(self, batch, batch_idx):
        return self._step(batch, self.train_metrics, 'train')

    def validation_step(self, batch, batch_idx):
        return self._step(batch, self.val_metrics, 'val')

    def test_step(self, batch, batch_idx):
        return self._step(batch, self.test_metrics, 'test')

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.hparams.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {"scheduler": scheduler, "monitor": "val_loss"}
        }

def setup_directories():
    """Setup necessary directories for training."""
    # Create directories
    base_dir = os.getcwd()
    checkpoint_dir = os.path.join(base_dir, 'checkpoints')
    os.makedirs(checkpoint_dir, exist_ok=True)
    return base_dir, checkpoint_dir

def get_callbacks(checkpoint_dir):
    """Get training callbacks."""
    callbacks = [
        ModelCheckpoint(
            dirpath=checkpoint_dir,
            filename='model-{epoch:02d}-{val_loss:.3f}',
            save_top_k=3,
            monitor='val_loss',
            mode='min'
        ),
        EarlyStopping(
            monitor='val_loss',
            patience=10,
            mode='min'
        ),
        LearningRateMonitor(logging_interval='epoch')
    ]
    return callbacks

def create_trainer(callbacks, max_epochs=100):
    """Create a PyTorch Lightning trainer."""
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        callbacks=callbacks,
        logger=TensorBoardLogger('lightning_logs', name='crypto_predictor'),
        accelerator='auto',
        devices=1,
        enable_progress_bar=True,
        enable_model_summary=True,
        log_every_n_steps=1
    )
    return trainer

def train_model(trainer, model, data_module):
    """Train the model and return best score."""
    try:
        trainer.fit(model, datamodule=data_module)
        return trainer.callback_metrics.get('val_loss', None)
    except Exception as e:
        print(f"Training error: {str(e)}")
        raise 
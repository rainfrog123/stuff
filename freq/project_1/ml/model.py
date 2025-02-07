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
        self.layer3 = nn.Linear(hidden_dim, 2)  # 2 output classes for binary classification
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout)
        
        self.learning_rate = learning_rate

        # Metrics for WIN class (class 1)
        self.train_precision = Precision(task='binary')
        self.train_recall = Recall(task='binary')
        self.train_f1 = F1Score(task='binary')
        
        self.val_precision = Precision(task='binary')
        self.val_recall = Recall(task='binary')
        self.val_f1 = F1Score(task='binary')
        
        self.test_precision = Precision(task='binary')
        self.test_recall = Recall(task='binary')
        self.test_f1 = F1Score(task='binary')

    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = self.dropout(x)
        x = F.relu(self.layer2(x))
        x = self.dropout(x)
        return self.layer3(x)  # Raw logits, no activation needed due to cross entropy loss

    def training_step(self, batch, batch_idx):
        x, y = batch
        y = y.squeeze()  # Remove extra dimension from targets
        logits = self(x)
        loss = F.cross_entropy(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        # Calculate WIN class metrics
        probs = F.softmax(logits, dim=1)[:, 1]  # Probability of WIN class
        precision = self.train_precision(probs, y)
        recall = self.train_recall(probs, y)
        f1 = self.train_f1(probs, y)
        
        # Log metrics
        self.log('train_loss', loss, prog_bar=True)
        self.log('train_acc', acc, prog_bar=True)
        self.log('train_win_precision', precision, prog_bar=True)
        self.log('train_win_recall', recall, prog_bar=True)
        self.log('train_win_f1', f1, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        y = y.squeeze()  # Remove extra dimension from targets
        logits = self(x)
        val_loss = F.cross_entropy(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        # Calculate WIN class metrics
        probs = F.softmax(logits, dim=1)[:, 1]  # Probability of WIN class
        precision = self.val_precision(probs, y)
        recall = self.val_recall(probs, y)
        f1 = self.val_f1(probs, y)
        
        # Log metrics
        self.log('val_loss', val_loss, prog_bar=True)
        self.log('val_acc', acc, prog_bar=True)
        self.log('val_win_precision', precision, prog_bar=True)
        self.log('val_win_recall', recall, prog_bar=True)
        self.log('val_win_f1', f1, prog_bar=True)
        return val_loss

    def test_step(self, batch, batch_idx):
        x, y = batch
        y = y.squeeze()  # Remove extra dimension from targets
        logits = self(x)
        test_loss = F.cross_entropy(logits, y)
        
        # Calculate accuracy
        preds = torch.argmax(logits, dim=1)
        acc = (preds == y).float().mean()
        
        # Calculate WIN class metrics
        probs = F.softmax(logits, dim=1)[:, 1]  # Probability of WIN class
        precision = self.test_precision(probs, y)
        recall = self.test_recall(probs, y)
        f1 = self.test_f1(probs, y)
        
        # Log metrics
        self.log('test_loss', test_loss)
        self.log('test_acc', acc)
        self.log('test_win_precision', precision)
        self.log('test_win_recall', recall)
        self.log('test_win_f1', f1)
        return test_loss

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
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
                "monitor": "val_loss"
            }
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
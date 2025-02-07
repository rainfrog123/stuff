import os
import shutil
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning import Trainer
from pytorch_lightning.loggers import TensorBoardLogger

def clear_tensorboard_logs():
    """Clear all tensorboard logs."""
    log_dir = os.path.join(os.getcwd(), 'lightning_logs')
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
        print("Tensorboard logs cleared.")

def setup_directories():
    directory_path = os.path.join(os.getcwd(), 'data')
    checkpoint_dir = os.path.join(os.getcwd(), 'checkpoints')
    os.makedirs(directory_path, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)
    return directory_path, checkpoint_dir

def get_callbacks(checkpoint_dir):
    return [
        EarlyStopping(
            monitor='val_loss',
            mode='min',
            patience=15,
            min_delta=0.001,
            verbose=True
        ),
        ModelCheckpoint(
            monitor='val_loss',
            dirpath=checkpoint_dir,
            filename='model-{epoch:02d}-{val_loss:.3f}',
            save_top_k=3,
            mode='min',
            verbose=True
        )
    ]

def create_trainer(callbacks, *, max_epochs=100):
    """Create a PyTorch Lightning trainer.
    
    Args:
        callbacks: List of callbacks to use during training
        max_epochs: Maximum number of epochs to train for (default: 100)
    """
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
    try:
        trainer.fit(model, datamodule=data_module)
        return trainer.checkpoint_callback.best_model_score
    except Exception as e:
        print(f"Training error: {str(e)}")
        raise 
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
import torch
import os
import shutil
from config import MAX_EPOCHS

def setup_trainer(trial_number=None, checkpoint_dir=None, tensorboard_dir=None):
    """Setup PyTorch Lightning trainer with proper configuration."""
    if trial_number is not None:
        # Setup trial directories
        trial_dir = os.path.join(checkpoint_dir, f'trial_{trial_number}')
        trial_log_dir = os.path.join(tensorboard_dir, f'trial_{trial_number}')
        
        # Clean up existing directories
        for dir_path in [trial_dir, trial_log_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path)
    else:
        trial_dir = checkpoint_dir
        trial_log_dir = tensorboard_dir

    # Setup callbacks
    callbacks = [
        ModelCheckpoint(
            dirpath=trial_dir,
            filename='best-{epoch:02d}-{val_loss:.3f}',
            save_top_k=1,
            monitor='val_loss',
            mode='min'
        ),
        EarlyStopping(
            monitor='val_loss',
            patience=5,
            mode='min'
        ),
        LearningRateMonitor(logging_interval='epoch')
    ]
    
    # Add trial pruning callback if in optimization mode
    if trial_number is not None:
        from optuna.integration import PyTorchLightningPruningCallback
        callbacks.append(PyTorchLightningPruningCallback(trial, monitor="val_loss"))

    # Setup logger
    logger = TensorBoardLogger(
        save_dir=tensorboard_dir,
        name=f'trial_{trial_number}' if trial_number is not None else 'training',
        version=0,
        default_hp_metric=False
    )

    # Configure trainer based on hardware
    trainer_kwargs = {
        'max_epochs': MAX_EPOCHS,
        'callbacks': callbacks,
        'logger': logger,
        'enable_progress_bar': True,
        'enable_model_summary': True,
        'log_every_n_steps': 1,
        'deterministic': True
    }

    # Add accelerator config
    if torch.cuda.is_available():
        trainer_kwargs.update({
            'accelerator': 'gpu',
            'devices': [0],
            'precision': '32-true'
        })
    else:
        trainer_kwargs.update({
            'accelerator': 'cpu',
            'devices': 'auto'
        })

    return pl.Trainer(**trainer_kwargs) 
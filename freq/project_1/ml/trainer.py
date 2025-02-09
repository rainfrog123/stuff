import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
import os
from config import MAX_EPOCHS

class TrainerFactory:
    @staticmethod
    def create_trainer(checkpoint_dir, tensorboard_dir):
        """Create a PyTorch Lightning trainer with proper configuration.
        
        Args:
            checkpoint_dir: Directory to save checkpoints
            tensorboard_dir: Directory for tensorboard logs
        """
        # Setup callbacks
        callbacks = [
            ModelCheckpoint(
                dirpath=checkpoint_dir,
                filename='best-{epoch:02d}-{val_loss:.3f}',
                save_top_k=1,
                monitor='val_loss',
                mode='min'
            ),
            EarlyStopping(
                monitor='val_loss',
                patience=15,
                min_delta=0.001,
                mode='min',
                verbose=True
            ),
            LearningRateMonitor(logging_interval='epoch')
        ]

        # Setup logger
        logger = TensorBoardLogger(
            save_dir=tensorboard_dir,
            name='crypto_predictor',
            version=0,
            default_hp_metric=False
        )

        # Create trainer
        trainer = pl.Trainer(
            max_epochs=MAX_EPOCHS,
            callbacks=callbacks,
            logger=logger,
            accelerator='auto',
            devices=1,
            enable_progress_bar=True,
            enable_model_summary=True,
            log_every_n_steps=1
        )
        
        return trainer

    @staticmethod
    def train_model(trainer, model, data_module):
        """Train the model and return best validation score.
        
        Args:
            trainer: PyTorch Lightning trainer
            model: Model to train
            data_module: Data module for training
            
        Returns:
            Best validation score achieved during training
        """
        try:
            trainer.fit(model, datamodule=data_module)
            return trainer.callback_metrics.get('val_loss')
        except Exception as e:
            print(f"Training error: {str(e)}")
            raise 
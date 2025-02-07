from data_module import CryptoDataModule
from model import CryptoPricePredictor
from optimization import run_optuna_optimization, run_ray_optimization
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import TensorBoardLogger
import pytorch_lightning as pl

if __name__ == "__main__":
    # Initialize with deterministic behavior
    pl.seed_everything(42)
    
    # Directory setup
    directory_path = '/allah/data/parquet'
    
    # Initialize data module
    data_module = CryptoDataModule(
        directory_path=directory_path,
        batch_size=64,
        num_workers=4,
        n_features=20
    )
    data_module.setup()

    # Model initialization
    model = CryptoPricePredictor(input_dim=data_module.input_dim)

    # Callbacks
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            mode='min',
            patience=15,
            min_delta=0.001,
            verbose=True
        ),
        ModelCheckpoint(
            monitor='val_loss',
            dirpath='checkpoints',
            filename='model-{epoch:02d}-{val_loss:.3f}',
            save_top_k=3,
            mode='min',
            verbose=True
        )
    ]

    # Initialize trainer
    trainer = Trainer(
        max_epochs=100,
        callbacks=callbacks,
        logger=True,
        accelerator='auto',
        devices=1,
        enable_progress_bar=True,
        enable_model_summary=True,
        log_every_n_steps=1
    )

    # Train model
    try:
        trainer.fit(model, datamodule=data_module)
        print(f"Best validation loss: {trainer.checkpoint_callback.best_model_score:.4f}")
    except Exception as e:
        print(f"Training error: {str(e)}")
        raise 
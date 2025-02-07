import optuna
from ray import tune
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping
from functools import partial

def run_optuna_optimization(trial, data_module, model_class):
    # Hyperparameters to optimize
    hidden_dim = trial.suggest_int('hidden_dim', 32, 256)
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-4, 1e-2)
    
    # Create model with trial parameters
    model = model_class(
        input_dim=data_module.input_dim,
        hidden_dim=hidden_dim,
        learning_rate=learning_rate
    )
    
    # Training
    trainer = pl.Trainer(
        max_epochs=50,
        callbacks=[EarlyStopping(monitor='val_loss', patience=5)],
        enable_progress_bar=False
    )
    
    trainer.fit(model, datamodule=data_module)
    
    return trainer.callback_metrics['val_loss'].item()

def run_ray_optimization(config, data_module, model_class):
    model = model_class(
        input_dim=data_module.input_dim,
        hidden_dim=config['hidden_dim'],
        learning_rate=config['learning_rate']
    )
    
    trainer = pl.Trainer(
        max_epochs=50,
        callbacks=[EarlyStopping(monitor='val_loss', patience=5)],
        enable_progress_bar=False
    )
    
    trainer.fit(model, datamodule=data_module)
    
    tune.report(val_loss=trainer.callback_metrics['val_loss'].item()) 
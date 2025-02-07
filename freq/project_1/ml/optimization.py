import optuna
import numpy as np
from trainer import setup_trainer
from config import (
    FEATURE_RANGE, HIDDEN_DIM_RANGE, LEARNING_RATE_RANGE,
    DROPOUT_RANGE, BATCH_SIZES, N_TRIALS
)

class CryptoOptimizer:
    def __init__(self, data_module, model_class, checkpoint_dir, tensorboard_dir):
        self.data_module = data_module
        self.model_class = model_class
        self.checkpoint_dir = checkpoint_dir
        self.tensorboard_dir = tensorboard_dir
        
        # Verify data module is ready
        try:
            self.data_module.prepare_data()
        except Exception as e:
            raise RuntimeError(f"Data module initialization failed: {str(e)}")

    def _select_features(self, n_features):
        """Select random features ensuring data is loaded."""
        if self.data_module._features_data is None:
            try:
                self.data_module._load_data()
            except Exception as e:
                raise RuntimeError(f"Failed to load features data: {str(e)}")
                
        total_features = self.data_module._features_data.shape[1]
        if n_features > total_features:
            raise ValueError(f"Requested {n_features} features but only {total_features} available")
            
        selected_features = np.random.choice(total_features, size=n_features, replace=False)
        selected_features.sort()
        return selected_features

    def objective(self, trial):
        """Optuna objective function for hyperparameter optimization."""
        try:
            # Hyperparameters to optimize
            n_features = trial.suggest_int('n_features', *FEATURE_RANGE)
            hidden_dim = trial.suggest_int('hidden_dim', *HIDDEN_DIM_RANGE)
            learning_rate = trial.suggest_float('learning_rate', *LEARNING_RATE_RANGE, log=True)
            dropout = trial.suggest_float('dropout', *DROPOUT_RANGE)
            batch_size = trial.suggest_categorical('batch_size', BATCH_SIZES)
            
            # Select features
            try:
                selected_features = self._select_features(n_features)
            except Exception as e:
                print(f"Feature selection failed: {str(e)}")
                raise optuna.exceptions.TrialPruned()
            
            # Update data module with selected features and batch size
            self.data_module.feature_indices = selected_features
            self.data_module.batch_size = batch_size
            
            # Setup data module
            try:
                self.data_module.setup('fit')
            except Exception as e:
                print(f"Data module setup failed: {str(e)}")
                raise optuna.exceptions.TrialPruned()
            
            # Initialize model with trial parameters
            try:
                model = self.model_class(
                    input_dim=n_features,
                    hidden_dim=hidden_dim,
                    learning_rate=learning_rate,
                    dropout=dropout
                )
            except Exception as e:
                print(f"Model initialization failed: {str(e)}")
                raise optuna.exceptions.TrialPruned()
            
            # Create trainer
            try:
                trainer = setup_trainer(
                    trial_number=trial.number,
                    checkpoint_dir=self.checkpoint_dir,
                    tensorboard_dir=self.tensorboard_dir
                )
            except Exception as e:
                print(f"Trainer setup failed: {str(e)}")
                raise optuna.exceptions.TrialPruned()
            
            # Train and get results
            try:
                trainer.fit(model, datamodule=self.data_module)
            except Exception as e:
                print(f"Training failed: {str(e)}")
                raise optuna.exceptions.TrialPruned()
            
            # Get best validation loss
            val_loss = trainer.callback_metrics.get('val_loss', float('inf'))
            if not isinstance(val_loss, float):
                val_loss = float(val_loss.cpu().numpy())
            
            # Store additional metrics
            metrics = trainer.callback_metrics
            trial.set_user_attr('selected_features', selected_features.tolist())
            trial.set_user_attr('val_acc', float(metrics.get('val_acc', 0)))
            trial.set_user_attr('val_win_f1', float(metrics.get('val_win_f1', 0)))
            
            return val_loss
            
        except Exception as e:
            print(f"Trial {trial.number} failed with error: {str(e)}")
            raise optuna.exceptions.TrialPruned()

    def optimize(self, n_trials=N_TRIALS):
        """Run the optimization process."""
        try:
            # Create study with more robust settings
            storage = optuna.storages.InMemoryStorage()
            study = optuna.create_study(
                direction="minimize",
                pruner=optuna.pruners.MedianPruner(n_warmup_steps=10),
                storage=storage,
                study_name="crypto_prediction_optimization"
            )
            
            # Run optimization
            print(f"\nRunning {n_trials} optimization trials...")
            study.optimize(self.objective, n_trials=n_trials, catch=(Exception,))
            
            return study
            
        except KeyboardInterrupt:
            print("\nOptimization interrupted by user.")
            if study.trials:
                return study
        except Exception as e:
            print(f"\nOptimization failed with error: {str(e)}")
            return None 
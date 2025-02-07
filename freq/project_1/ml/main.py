# Imports
from data_module import CryptoDataModule
from model import CryptoPricePredictor
from trainer_module import setup_directories, get_callbacks, create_trainer, train_model, clear_tensorboard_logs
import pytorch_lightning as pl
from torchinfo import summary
import numpy as np
from collections import defaultdict
import json
import os

# Setup
# clear_tensorboard_logs()
pl.seed_everything(42)
directory_path, checkpoint_dir = setup_directories()

# Initialize data module first to get total features
base_data_module = CryptoDataModule(directory_path='/allah/data/parquet', batch_size=64, num_workers=4)
base_data_module.setup()
total_features = base_data_module.input_dim

# Storage for results
results = []
best_features = None
best_score = float('inf')
best_metrics = None

# Run 100 experiments
for experiment in range(100):
    print(f"\nExperiment {experiment + 1}/100")
    
    # Randomly select 100 features
    selected_features = np.random.choice(total_features, size=100, replace=False)
    selected_features.sort()  # Sort for consistent ordering
    
    # Initialize data module with selected features
    data_module = CryptoDataModule(
        directory_path='/allah/data/parquet',
        batch_size=64,
        num_workers=4,
        feature_indices=selected_features
    )
    data_module.setup()
    
    # Initialize model
    model = CryptoPricePredictor(input_dim=100)  # 100 selected features
    
    # Train
    trainer = create_trainer(get_callbacks(checkpoint_dir))
    val_loss = train_model(trainer, model, data_module)
    
    # Get metrics and convert tensors to float
    metrics = trainer.callback_metrics
    experiment_results = {
        'experiment': experiment + 1,
        'val_loss': float(val_loss) if val_loss is not None else None,
        'val_acc': float(metrics.get('val_acc', 0)),
        'val_win_precision': float(metrics.get('val_win_precision', 0)),
        'val_win_recall': float(metrics.get('val_win_recall', 0)),
        'val_win_f1': float(metrics.get('val_win_f1', 0)),
        'selected_features': selected_features.tolist()
    }
    results.append(experiment_results)
    
    # Update best if current is better
    if val_loss is not None and val_loss < best_score:
        best_score = float(val_loss)
        best_features = selected_features.tolist()
        best_metrics = experiment_results.copy()
        
        # Save best features
        with open('best_features.json', 'w') as f:
            json.dump({
                'features': best_features,
                'metrics': best_metrics
            }, f, indent=4)
    
    print(f"Val Loss: {val_loss:.4f}")
    print(f"Val Accuracy: {float(metrics.get('val_acc', 0)):.4f}")
    print(f"Val WIN F1: {float(metrics.get('val_win_f1', 0)):.4f}")

# Save all results
with open('experiment_results.json', 'w') as f:
    json.dump(results, f, indent=4)

# Print best results
print("\nBest Experiment Results:")
print(f"Best Validation Loss: {best_score:.4f}")
print(f"Best Validation Accuracy: {best_metrics['val_acc']:.4f}")
print(f"Best Validation WIN Precision: {best_metrics['val_win_precision']:.4f}")
print(f"Best Validation WIN Recall: {best_metrics['val_win_recall']:.4f}")
print(f"Best Validation WIN F1: {best_metrics['val_win_f1']:.4f}")
print(f"\nBest Feature Indices saved to 'best_features.json'")
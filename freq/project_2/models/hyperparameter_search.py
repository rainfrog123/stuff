#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LSTM Hyperparameter Optimization
-----------------------------------------
This script uses Optuna to find the best hyperparameters
for the LSTM model to maximize precision for profitable trades.
"""

import os
import numpy as np
import torch
import optuna
from optuna.trial import Trial
import pytorch_lightning as pl
import matplotlib.pyplot as plt
import json
from datetime import datetime
from lstm_trainer import LSTMDataModule, BasicLSTMModel, train_model, launch_tensorboard
import argparse


def objective(trial: Trial, data_dir: str, file_prefix: str, num_epochs: int = 30, log_dir: str = "logs") -> float:
    """
    Optuna objective function for hyperparameter optimization.
    Returns precision for profitable trades (class 1).
    """
    # Hyperparameter search space focused on maximizing precision
    hidden_size = trial.suggest_categorical("hidden_size", [128, 160, 192, 224, 256, 320])
    num_layers = trial.suggest_int("num_layers", 1, 3)
    dropout = trial.suggest_float("dropout", 0.2, 0.5)  # Higher dropout range to prevent overfitting
    learning_rate = trial.suggest_float("learning_rate", 5e-5, 5e-3, log=True)  # Narrower LR range
    weight_decay = trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True)  # More regularization
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
    
    # Additional model architecture parameters
    fc_size = trial.suggest_categorical("fc_size", [64, 96, 128, 160])
    use_batch_norm = trial.suggest_categorical("use_batch_norm", [True, False])
    
    # Stronger emphasis on class weights for profitable trades
    class_weight_ratio = trial.suggest_float("class_weight_ratio", 1.5, 6.0)  # Higher weights for profitable class
    
    # Create unique name for this trial
    trial_name = f"trial_{trial.number}_h{hidden_size}_l{num_layers}_d{dropout:.2f}_lr{learning_rate:.6f}_cw{class_weight_ratio:.2f}"
    trial_log_dir = os.path.join(log_dir, trial_name)
    
    # Train model with these hyperparameters
    try:
        _, results = train_model(
            data_dir=data_dir,
            batch_size=batch_size,
            max_epochs=num_epochs,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            file_prefix=file_prefix,
            class_weight_ratio=class_weight_ratio,
            log_dir=trial_log_dir,
            fc_size=fc_size,
            use_batch_norm=use_batch_norm
        )
        
        # The metric we want to optimize (precision for profitable trades)
        precision = results["precision"]
        
        # Log other metrics 
        trial.set_user_attr("recall", results["recall"])
        trial.set_user_attr("f1", results["f1"])
        trial.set_user_attr("accuracy", results["accuracy"])
        
        return precision
    
    except Exception as e:
        print(f"Trial {trial.number} failed with error: {str(e)}")
        return 0.0  # Return lowest possible value if trial fails


def run_hyperparameter_search(data_dir: str, file_prefix: str, n_trials: int = 25, 
                              num_epochs: int = 30, log_dir: str = "logs"):
    """
    Run hyperparameter search with Optuna
    """
    # Set up GPU if available
    if torch.cuda.is_available():
        devices = 1
        accelerator = "gpu"
        print("Using GPU for training")
    else:
        devices = 1
        accelerator = "cpu"
        print("Using CPU for training")
    
    # Launch TensorBoard
    tb_thread = launch_tensorboard(log_dir, port=6006)
    
    # Create study
    study_name = f"lstm_hparam_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    storage_name = f"sqlite:///{study_name}.db"
    
    study = optuna.create_study(
        study_name=study_name, 
        storage=storage_name,
        direction="maximize",
        load_if_exists=True
    )
    
    # Run optimization
    try:
        study.optimize(
            lambda trial: objective(trial, data_dir, file_prefix, num_epochs, log_dir),
            n_trials=n_trials,
            show_progress_bar=True
        )
    except KeyboardInterrupt:
        print("Hyperparameter search interrupted!")
    
    # Display best parameters
    print("\nBest trial:")
    trial = study.best_trial
    print(f"  Value (Precision): {trial.value:.4f}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")
    
    # Get other metrics from best trial
    print("\nOther metrics for best trial:")
    print(f"  Recall: {trial.user_attrs.get('recall', 'N/A')}")
    print(f"  F1 Score: {trial.user_attrs.get('f1', 'N/A')}")
    print(f"  Accuracy: {trial.user_attrs.get('accuracy', 'N/A')}")
    
    # Save study results
    os.makedirs("results", exist_ok=True)
    
    # 1. Save best parameters to JSON
    best_params = {
        "precision": trial.value,
        "recall": trial.user_attrs.get("recall", 0),
        "f1": trial.user_attrs.get("f1", 0),
        "accuracy": trial.user_attrs.get("accuracy", 0),
        "params": trial.params
    }
    with open(f"results/best_params_{study_name}.json", "w") as f:
        json.dump(best_params, f, indent=4)
    
    # 2. Plot optimization history
    plt.figure(figsize=(10, 6))
    optuna.visualization.matplotlib.plot_optimization_history(study)
    plt.tight_layout()
    plt.savefig(f"results/optimization_history_{study_name}.png")
    
    # 3. Plot parameter importances
    plt.figure(figsize=(10, 6))
    optuna.visualization.matplotlib.plot_param_importances(study)
    plt.tight_layout()
    plt.savefig(f"results/param_importances_{study_name}.png")
    
    # 4. Plot parallel coordinate
    plt.figure(figsize=(12, 8))
    optuna.visualization.matplotlib.plot_parallel_coordinate(study)
    plt.tight_layout()
    plt.savefig(f"results/parallel_coordinate_{study_name}.png")
    
    # 5. Train a final model with the best parameters (for a longer duration if desired)
    print("\nTraining final model with best parameters...")
    
    final_model, final_results = train_model(
        data_dir=data_dir,
        batch_size=trial.params["batch_size"],
        max_epochs=num_epochs * 2,  # Train for longer
        learning_rate=trial.params["learning_rate"],
        weight_decay=trial.params["weight_decay"],
        hidden_size=trial.params["hidden_size"],
        num_layers=trial.params["num_layers"],
        dropout=trial.params["dropout"],
        file_prefix=file_prefix,
        class_weight_ratio=trial.params["class_weight_ratio"],
        log_dir=os.path.join(log_dir, "final_model"),
        fc_size=trial.params["fc_size"],
        use_batch_norm=trial.params["use_batch_norm"]
    )
    
    # Save final model results
    final_results_path = f"results/final_model_results_{study_name}.json"
    with open(final_results_path, "w") as f:
        json.dump(final_results, f, indent=4)
    
    print(f"Final model results saved to {final_results_path}")
    print(f"Best hyperparameters saved to results/best_params_{study_name}.json")
    
    return study


def main():
    """Main entry point"""
    # Hardcoded parameter settings
    
    # Data parameters
    data_dir = "./lstm_data"
    file_prefix = "trade_outcome_data"
    
    # Search parameters
    n_trials = 20
    epochs_per_trial = 20
    log_dir = "logs/hparam_search"
    
    # Create log directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Print search configuration
    print("\n" + "="*80)
    print("Starting Hyperparameter Search with the following configuration:")
    print(f"Data directory: {data_dir}")
    print(f"File prefix: {file_prefix}")
    print(f"Number of trials: {n_trials}")
    print(f"Epochs per trial: {epochs_per_trial}")
    print(f"Log directory: {log_dir}")
    print("="*80 + "\n")
    
    # Run hyperparameter search
    study = run_hyperparameter_search(
        data_dir=data_dir,
        file_prefix=file_prefix,
        n_trials=n_trials,
        num_epochs=epochs_per_trial,
        log_dir=log_dir
    )
    
    print("\nHyperparameter search completed!")
    print(f"Best precision: {study.best_value:.4f}")
    

if __name__ == "__main__":
    main() 
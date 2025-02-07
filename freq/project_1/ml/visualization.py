import optuna
import json
from optuna.visualization import plot_optimization_history, plot_param_importances

def save_study_results(study, output_dir='.'):
    """Save optimization results and visualizations."""
    try:
        if not study.trials:
            print("No trials to save.")
            return
            
        # Get best trial
        trial = study.best_trial
        
        # Prepare results
        results = {
            'best_params': trial.params,
            'best_value': trial.value,
            'best_features': trial.user_attrs.get('selected_features', []),
            'best_metrics': {
                'val_acc': trial.user_attrs.get('val_acc', 0),
                'val_win_f1': trial.user_attrs.get('val_win_f1', 0)
            },
            'all_trials': [
                {
                    'number': t.number,
                    'params': t.params,
                    'value': t.value if t.value is not None else float('inf'),
                    'state': t.state.name
                }
                for t in study.trials
            ]
        }
        
        # Save results
        with open(f'{output_dir}/optimization_results.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        # Save visualizations
        try:
            if len(study.trials) > 1:
                fig = plot_optimization_history(study)
                fig.write_html(f"{output_dir}/optimization_history.html")
                
                fig = plot_param_importances(study)
                fig.write_html(f"{output_dir}/param_importances.html")
                
                print("\nVisualization files created: optimization_history.html, param_importances.html")
        except Exception as e:
            print(f"Could not generate visualizations: {str(e)}")
        
        # Print results
        print_optimization_results(trial)
        
    except Exception as e:
        print(f"Error saving results: {str(e)}")

def print_optimization_results(trial):
    """Print optimization results in a formatted way."""
    print("\nBest trial:")
    print(f"\nBest Hyperparameters:")
    print(f"Number of features: {trial.params['n_features']}")
    print(f"Hidden dimensions: {trial.params['hidden_dim']}")
    print(f"Learning rate: {trial.params['learning_rate']:.6f}")
    print(f"Dropout rate: {trial.params['dropout']:.3f}")
    print(f"Batch size: {trial.params['batch_size']}")
    
    print(f"\nBest Metrics:")
    print(f"Validation Loss: {trial.value:.4f}")
    print(f"Validation Accuracy: {trial.user_attrs['val_acc']:.4f}")
    print(f"Validation WIN F1: {trial.user_attrs['val_win_f1']:.4f}") 
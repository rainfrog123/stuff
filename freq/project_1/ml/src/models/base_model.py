from abc import ABC, abstractmethod
import pytorch_lightning as pl
import torch
import torch.nn as nn
from torchmetrics import Precision, Recall, F1Score
from typing import Dict, Any, Tuple

class BaseModel(pl.LightningModule, ABC):
    """Base model class with common functionality."""
    
    def __init__(self, learning_rate: float = 1e-3):
        super().__init__()
        self.learning_rate = learning_rate
        
        # Initialize metrics
        self.train_metrics = self._create_metrics()
        self.val_metrics = self._create_metrics()
        self.test_metrics = self._create_metrics()
        
    def _create_metrics(self) -> Dict[str, Any]:
        """Create a set of metrics for training/validation/testing."""
        return {
            'precision': Precision(task='binary'),
            'recall': Recall(task='binary'),
            'f1': F1Score(task='binary')
        }
        
    def _compute_metrics(self, metrics: Dict[str, Any], logits: torch.Tensor, 
                        targets: torch.Tensor, prefix: str) -> Dict[str, torch.Tensor]:
        """Compute and log metrics.
        
        Args:
            metrics: Dictionary of metric objects
            logits: Model output logits
            targets: Ground truth labels
            prefix: Prefix for metric names (e.g., 'train', 'val', 'test')
            
        Returns:
            Dictionary of computed metric values
        """
        probs = torch.softmax(logits, dim=1)[:, 1]  # Probability of positive class
        results = {}
        
        # Calculate metrics
        for name, metric in metrics.items():
            value = metric(probs, targets)
            self.log(f'{prefix}_{name}', value, prog_bar=True)
            results[name] = value
            
        return results
        
    def _step(self, batch: Tuple[torch.Tensor, torch.Tensor], metrics: Dict[str, Any], 
              prefix: str) -> Dict[str, torch.Tensor]:
        """Common step for training/validation/testing.
        
        Args:
            batch: Tuple of (features, targets)
            metrics: Dictionary of metric objects
            prefix: Prefix for metric names
            
        Returns:
            Dictionary with loss and metrics
        """
        x, y = batch
        y = y.squeeze()
        
        # Get model predictions
        logits = self(x)
        loss = nn.functional.cross_entropy(logits, y)
        
        # Log loss
        self.log(f'{prefix}_loss', loss, prog_bar=True)
        
        # Compute metrics
        metric_values = self._compute_metrics(metrics, logits, y, prefix)
        
        return {'loss': loss, **metric_values}
        
    def training_step(self, batch: Tuple[torch.Tensor, torch.Tensor], 
                     batch_idx: int) -> Dict[str, torch.Tensor]:
        """Training step."""
        return self._step(batch, self.train_metrics, 'train')
        
    def validation_step(self, batch: Tuple[torch.Tensor, torch.Tensor], 
                       batch_idx: int) -> Dict[str, torch.Tensor]:
        """Validation step."""
        return self._step(batch, self.val_metrics, 'val')
        
    def test_step(self, batch: Tuple[torch.Tensor, torch.Tensor], 
                  batch_idx: int) -> Dict[str, torch.Tensor]:
        """Test step."""
        return self._step(batch, self.test_metrics, 'test')
        
    def configure_optimizers(self):
        """Configure optimizer and learning rate scheduler."""
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
        
    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the model.
        
        Args:
            x: Input tensor
            
        Returns:
            Model output tensor
        """
        pass 
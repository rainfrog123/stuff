import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any
from .base_model import BaseModel

class CryptoPricePredictor(BaseModel):
    """Neural network model for crypto price prediction."""
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, 
                 dropout: float = 0.2, learning_rate: float = 1e-3):
        """Initialize the model.
        
        Args:
            input_dim: Number of input features
            hidden_dim: Number of hidden units
            dropout: Dropout rate
            learning_rate: Learning rate for optimization
        """
        super().__init__(learning_rate=learning_rate)
        self.save_hyperparameters()
        
        # Network layers
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.layer3 = nn.Linear(hidden_dim, 2)  # Binary classification
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the model.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
            
        Returns:
            Output tensor of shape (batch_size, 2)
        """
        x = F.relu(self.layer1(x))
        x = self.dropout(x)
        x = F.relu(self.layer2(x))
        x = self.dropout(x)
        return self.layer3(x) 
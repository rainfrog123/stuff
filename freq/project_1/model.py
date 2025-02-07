import torch
import torch.nn as nn
import torch.nn.functional as F
import pytorch_lightning as pl

class CryptoPricePredictor(pl.LightningModule):
    def __init__(self, input_dim=20, hidden_dims=[512, 256, 128], dropout_rate=0.3, learning_rate=1e-3):
        super().__init__()
        self.save_hyperparameters()
        
        # Initialize class weights
        self.register_buffer('class_weights', torch.tensor([1.0, 1.0]))
        
        # Model architecture
        layers = []
        dims = [input_dim] + hidden_dims
        
        for i in range(len(dims)-1):
            layers.extend([
                nn.Linear(dims[i], dims[i+1]),
                nn.BatchNorm1d(dims[i+1]),
                nn.LeakyReLU(0.1),
                nn.Dropout(dropout_rate)
            ])
        
        layers.append(nn.Linear(dims[-1], 2))
        self.model = nn.Sequential(*layers)
        self.learning_rate = learning_rate

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = F.cross_entropy(logits, y, weight=self.class_weights)
        
        self.log('train_loss', loss, on_step=True, on_epoch=True, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x)
        loss = F.cross_entropy(logits, y, weight=self.class_weights)
        
        self.log('val_loss', loss, on_step=False, on_epoch=True, prog_bar=True)
        return loss

    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(self.parameters(), lr=self.learning_rate)
        return optimizer 
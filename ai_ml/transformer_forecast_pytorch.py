"""
Transformer-based Time Series Forecasting (PyTorch Implementation)
Self-attention mechanism for capturing long-term dependencies
Compatible with numpy>=2.2.3
"""

import numpy as np
import math
import warnings
from typing import Dict, Tuple, Optional, List
warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    print("PyTorch not available. Install with: pip install torch")

# Import LSTMPricePredictor for HybridPredictor
try:
    from .lstm_forecast_pytorch import LSTMPricePredictor
except ImportError:
    try:
        from ai_ml.lstm_forecast_pytorch import LSTMPricePredictor
    except ImportError:
        LSTMPricePredictor = None


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        return x + self.pe[:, :x.size(1), :]


class TransformerBlock(nn.Module):
    """Transformer encoder block"""
    
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, dropout: float = 0.1):
        super().__init__()
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, ff_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ff_dim, embed_dim)
        )
        self.layernorm1 = nn.LayerNorm(embed_dim)
        self.layernorm2 = nn.LayerNorm(embed_dim)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
    
    def forward(self, x):
        # Self-attention
        attn_out, _ = self.attention(x, x, x)
        attn_out = self.dropout1(attn_out)
        out1 = self.layernorm1(x + attn_out)
        
        # Feed-forward
        ffn_out = self.ffn(out1)
        ffn_out = self.dropout2(ffn_out)
        return self.layernorm2(out1 + ffn_out)


class TransformerModel(nn.Module):
    """Transformer model for time series prediction"""
    
    def __init__(
        self,
        input_size: int = 1,
        embed_dim: int = 128,
        num_heads: int = 4,
        ff_dim: int = 256,
        num_layers: int = 3,
        dropout: float = 0.1,
        sequence_length: int = 60
    ):
        super().__init__()
        self.embed_dim = embed_dim
        
        # Input projection
        self.input_projection = nn.Linear(input_size, embed_dim)
        
        # Positional encoding
        self.pos_encoding = PositionalEncoding(embed_dim, max_len=sequence_length)
        
        # Transformer blocks
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(embed_dim, num_heads, ff_dim, dropout)
            for _ in range(num_layers)
        ])
        
        # Output layers
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        
        # Project to embed_dim
        x = self.input_projection(x)
        
        # Add positional encoding
        x = self.pos_encoding(x)
        
        # Apply transformer blocks
        for transformer in self.transformer_blocks:
            x = transformer(x)
        
        # Global average pooling
        x = x.permute(0, 2, 1)  # (batch, embed_dim, seq_len)
        x = self.global_pool(x).squeeze(-1)  # (batch, embed_dim)
        
        # Output
        return self.fc(x)


class TransformerPricePredictor:
    """
    Transformer-based Price Predictor (PyTorch)
    Uses self-attention to capture long-range dependencies
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        num_heads: int = 4,
        embed_dim: int = 128,
        ff_dim: int = 256,
        num_layers: int = 3,
        dropout_rate: float = 0.1,
        learning_rate: float = 0.0001
    ):
        """
        Initialize Transformer predictor
        
        Args:
            sequence_length: Lookback window size
            num_heads: Number of attention heads
            embed_dim: Embedding dimension
            ff_dim: Feed-forward dimension
            num_layers: Number of transformer layers
            dropout_rate: Dropout rate
            learning_rate: Learning rate
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required. Install with: pip install torch")
        
        self.sequence_length = sequence_length
        self.num_heads = num_heads
        self.embed_dim = embed_dim
        self.ff_dim = ff_dim
        self.num_layers = num_layers
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None
        self.is_fitted = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def _build_model(self):
        """Build Transformer model"""
        self.model = TransformerModel(
            input_size=1,
            embed_dim=self.embed_dim,
            num_heads=self.num_heads,
            ff_dim=self.ff_dim,
            num_layers=self.num_layers,
            dropout=self.dropout_rate,
            sequence_length=self.sequence_length
        ).to(self.device)
    
    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize data using z-score normalization"""
        if self.scaler_mean is None:
            self.scaler_mean = np.mean(data)
            self.scaler_std = np.std(data) + 1e-8
        return (data - self.scaler_mean) / self.scaler_std
    
    def _inverse_normalize(self, data: np.ndarray) -> np.ndarray:
        """Inverse normalization"""
        return data * self.scaler_std + self.scaler_mean
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create input/output sequences for training"""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length])
        return np.array(X), np.array(y)
    
    def fit(
        self,
        price_data: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: int = 1
    ) -> Dict:
        """
        Train the Transformer model
        
        Args:
            price_data: Historical price data
            epochs: Number of training epochs
            batch_size: Batch size for training
            verbose: Verbosity level
            
        Returns:
            Training history dictionary
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        
        # Normalize data
        normalized_data = self._normalize(price_data)
        
        # Create sequences
        X, y = self._create_sequences(normalized_data)
        
        if len(X) == 0:
            raise ValueError("Not enough data to create sequences")
        
        # Reshape: (batch, seq_len, features)
        X = X.reshape(-1, self.sequence_length, 1)
        y = y.reshape(-1, 1)
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)
        
        # Create data loader
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Build model
        self._build_model()
        
        # Training setup
        criterion = nn.HuberLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        
        # Training loop
        history = {'loss': [], 'mae': []}
        
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_mae = 0.0
            num_batches = 0
            
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                
                epoch_loss += loss.item()
                epoch_mae += torch.mean(torch.abs(outputs - batch_y)).item()
                num_batches += 1
            
            avg_loss = epoch_loss / num_batches
            avg_mae = epoch_mae / num_batches
            history['loss'].append(avg_loss)
            history['mae'].append(avg_mae)
            
            scheduler.step()
            
            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.6f} - MAE: {avg_mae:.6f}")
        
        self.is_fitted = True
        return history
    
    def predict(self, price_data: np.ndarray) -> float:
        """
        Predict next price
        
        Args:
            price_data: Recent price data (at least sequence_length points)
            
        Returns:
            Predicted next price
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # Normalize using existing parameters
        normalized_data = self._normalize(price_data)
        
        # Get last sequence
        if len(normalized_data) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} data points")
        
        sequence = normalized_data[-self.sequence_length:]
        sequence = sequence.reshape(1, self.sequence_length, 1)
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(sequence).to(self.device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(X_tensor).cpu().numpy()[0, 0]
        
        # Inverse normalize
        return float(self._inverse_normalize(prediction))
    
    def generate_signal(self, price_data: np.ndarray) -> Dict:
        """
        Generate trading signal based on prediction
        
        Args:
            price_data: Recent price data
            
        Returns:
            Dictionary with signal, confidence, and predicted price
        """
        if not self.is_fitted:
            return {
                'signal': 0,
                'confidence': 0.0,
                'predicted_price': None,
                'expected_change': 0.0
            }
        
        try:
            predicted_price = self.predict(price_data)
            current_price = float(price_data[-1])
            
            # Calculate expected change
            expected_change = (predicted_price - current_price) / current_price
            
            # Determine signal
            signal = 0
            if expected_change > 0.005:  # 0.5% threshold
                signal = 1
            elif expected_change < -0.005:
                signal = -1
            
            # Confidence based on attention consistency (simplified)
            confidence = min(0.85, abs(expected_change) * 8 + 0.5)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'predicted_price': predicted_price,
                'expected_change': expected_change
            }
        except Exception as e:
            print(f"Signal generation error: {e}")
            return {
                'signal': 0,
                'confidence': 0.0,
                'predicted_price': None,
                'expected_change': 0.0
            }
    
    def get_statistics(self) -> Dict:
        """Get model statistics"""
        return {
            'model_type': 'transformer_pytorch',
            'sequence_length': self.sequence_length,
            'embed_dim': self.embed_dim,
            'num_heads': self.num_heads,
            'num_layers': self.num_layers,
            'is_fitted': self.is_fitted,
            'device': str(self.device)
        }


class HybridPredictor:
    """
    Hybrid model combining LSTM and Transformer predictions
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 64,
        transformer_heads: int = 4,
        embed_dim: int = 64
    ):
        """Initialize Hybrid predictor"""
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        
        self.sequence_length = sequence_length
        self.lstm_predictor = LSTMPricePredictor(
            sequence_length=sequence_length,
            lstm_units=lstm_units
        )
        self.transformer_predictor = TransformerPricePredictor(
            sequence_length=sequence_length,
            num_heads=transformer_heads,
            embed_dim=embed_dim
        )
        self.is_fitted = False
    
    def fit(self, price_data: np.ndarray, epochs: int = 30, verbose: int = 0) -> Dict:
        """Train both models"""
        lstm_history = self.lstm_predictor.fit(price_data, epochs=epochs, verbose=verbose)
        transformer_history = self.transformer_predictor.fit(price_data, epochs=epochs, verbose=verbose)
        self.is_fitted = True
        return {'lstm': lstm_history, 'transformer': transformer_history}
    
    def predict(self, price_data: np.ndarray) -> float:
        """Ensemble prediction"""
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        lstm_pred = self.lstm_predictor.predict(price_data)
        transformer_pred = self.transformer_predictor.predict(price_data)
        
        # Weighted average (transformer gets slightly more weight)
        return 0.4 * lstm_pred + 0.6 * transformer_pred

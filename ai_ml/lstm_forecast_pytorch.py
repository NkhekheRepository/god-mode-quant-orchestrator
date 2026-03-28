"""
LSTM-based Time Series Forecasting (PyTorch Implementation)
Deep learning model for trading signal prediction
Compatible with numpy>=2.2.3
"""

import numpy as np
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
    nn = None  # Placeholder for type hints
    print("PyTorch not available. Install with: pip install torch")


if PYTORCH_AVAILABLE:
    class LSTMModel(nn.Module):
        """LSTM Neural Network for time series prediction"""

        def __init__(
            self,
            input_size: int = 1,
            hidden_size: int = 128,
            num_layers: int = 2,
            dropout: float = 0.2,
            bidirectional: bool = True
        ):
            super().__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.bidirectional = bidirectional

            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
                bidirectional=bidirectional
            )

            # Calculate output size based on bidirectional
            output_size = hidden_size * 2 if bidirectional else hidden_size

            self.fc = nn.Sequential(
                nn.Linear(output_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 1)
            )

        def forward(self, x):
            # x shape: (batch, seq_len, input_size)
            lstm_out, _ = self.lstm(x)
            # Take the last output
            last_output = lstm_out[:, -1, :]
            return self.fc(last_output)
else:
    # Stub class when PyTorch not available
    class LSTMModel:
        """Stub for LSTMModel when PyTorch not available"""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required for LSTMModel. Install with: pip install torch")


class LSTMPricePredictor:
    """
    LSTM Neural Network for Price Prediction (PyTorch)
    Captures temporal dependencies in time series data
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 128,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        bidirectional: bool = True
    ):
        """
        Initialize LSTM predictor
        
        Args:
            sequence_length: Lookback window size
            lstm_units: Number of LSTM units
            dropout_rate: Dropout rate for regularization
            learning_rate: Learning rate for optimizer
            bidirectional: Use bidirectional LSTM
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required. Install with: pip install torch")
        
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.bidirectional = bidirectional
        
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None
        self.is_fitted = False
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def _build_model(self):
        """Build LSTM model"""
        self.model = LSTMModel(
            input_size=1,
            hidden_size=self.lstm_units,
            num_layers=2,
            dropout=self.dropout_rate,
            bidirectional=self.bidirectional
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
        Train the LSTM model
        
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
        
        # Reshape for LSTM: (batch, seq_len, features)
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
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
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
            
            scheduler.step(avg_loss)
            
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
            
            # Confidence based on magnitude of change
            confidence = min(0.9, abs(expected_change) * 10 + 0.5)
            
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
            'model_type': 'lstm_pytorch',
            'sequence_length': self.sequence_length,
            'lstm_units': self.lstm_units,
            'bidirectional': self.bidirectional,
            'is_fitted': self.is_fitted,
            'device': str(self.device)
        }


class LSTMSignalGenerator(LSTMPricePredictor):
    """
    LSTM-based signal generator (alias for compatibility)
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 128,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        bidirectional: bool = True,
        confidence_threshold: float = 0.6  # Added for compatibility with ml_service
    ):
        """
        Initialize LSTM signal generator
        
        Args:
            sequence_length: Lookback window size
            lstm_units: Number of LSTM units
            dropout_rate: Dropout rate for regularization
            learning_rate: Learning rate for optimizer
            bidirectional: Use bidirectional LSTM
            confidence_threshold: Minimum confidence threshold for signals
        """
        super().__init__(
            sequence_length=sequence_length,
            lstm_units=lstm_units,
            dropout_rate=dropout_rate,
            learning_rate=learning_rate,
            bidirectional=bidirectional
        )
        self.confidence_threshold = confidence_threshold

"""
Transformer-based Time Series Forecasting
Self-attention mechanism for capturing long-term dependencies
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import (
        Input, Dense, Dropout, LayerNormalization,
        MultiHeadAttention, GlobalAveragePooling1D, Add
    )
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. Install with: pip install tensorflow")


class TransformerBlock(keras.layers.Layer):
    """
    Transformer encoder block with self-attention
    """
    
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, rate: float = 0.1):
        """
        Initialize Transformer block
        
        Args:
            embed_dim: Embedding dimension
            num_heads: Number of attention heads
            ff_dim: Feed-forward dimension
            rate: Dropout rate
        """
        super().__init__()
        self.att = MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = keras.Sequential([
            Dense(ff_dim, activation="gelu"),
            Dense(embed_dim),
        ])
        self.layernorm1 = LayerNormalization(epsilon=1e-6)
        self.layernorm2 = LayerNormalization(epsilon=1e-6)
        self.dropout1 = Dropout(rate)
        self.dropout2 = Dropout(rate)
    
    def call(self, inputs, training=False):
        """
        Forward pass
        
        Args:
            inputs: Input tensor
            training: Training mode
            
        Returns:
            Output tensor
        """
        attn_output = self.att(inputs, inputs, training=training)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        
        ffn_output = self.ffn(out1, training=training)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)


class TransformerPricePredictor:
    """
    Transformer-based time series forecaster
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
            sequence_length: Lookback window
            num_heads: Number of attention heads
            embed_dim: Embedding dimension
            ff_dim: Feed-forward dimension
            num_layers: Number of transformer blocks
            dropout_rate: Dropout rate
            learning_rate: Learning rate
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required. Install with: pip install tensorflow")
        
        self.sequence_length = sequence_length
        self.num_heads = num_heads
        self.embed_dim = embed_dim
        self.ff_dim = ff_dim
        self.num_layers = num_layers
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model = None
        self.is_fitted = False
    
    def positional_encoding(self, seq_len: int, d_model: int) -> tf.Tensor:
        """
        Create positional encoding
        
        Args:
            seq_len: Sequence length
            d_model: Model dimension
            
        Returns:
            Positional encoding tensor
        """
        positions = np.arange(seq_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        
        pe = np.zeros((seq_len, d_model))
        pe[:, 0::2] = np.sin(positions * div_term)
        pe[:, 1::2] = np.cos(positions * div_term)
        
        return tf.cast(pe[np.newaxis, :, :], dtype=tf.float32)
    
    def build_model(self, input_shape: tuple, num_features: int = 1) -> Model:
        """
        Build Transformer model
        
        Args:
            input_shape: Input shape (sequence_length, features)
            num_features: Number of input features
            
        Returns:
            Compiled Keras model
        """
        inputs = Input(shape=input_shape)
        
        # Add positional encoding
        pos_encoding = self.positional_encoding(input_shape[0], self.embed_dim)
        
        # Project input to embedding dimension
        x = Dense(self.embed_dim)(inputs)
        x = Add()([x, pos_encoding[:, :input_shape[0], :]])
        x = Dropout(self.dropout_rate)(x)
        
        # Stack transformer blocks
        for _ in range(self.num_layers):
            x = TransformerBlock(
                embed_dim=self.embed_dim,
                num_heads=self.num_heads,
                ff_dim=self.ff_dim,
                rate=self.dropout_rate
            )(x)
        
        # Global pooling
        x = GlobalAveragePooling1D()(x)
        
        # Dense layers
        x = Dense(64, activation='gelu')(x)
        x = Dropout(self.dropout_rate)(x)
        
        outputs = Dense(1, activation='linear')(x)
        
        model = Model(inputs=inputs, outputs=outputs)
        
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='huber_loss',
            metrics=['mae', 'mse']
        )
        
        return model
    
    def prepare_sequences(
        self,
        data: np.ndarray,
        target: np.ndarray = None
    ) -> tuple:
        """
        Prepare sequences for training
        
        Args:
            data: Input data
            target: Target values
            
        Returns:
            X, y sequences
        """
        X, y = [], []
        
        if target is None:
            target = data[1:]
            data = data[:-1]
        
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(target[i + self.sequence_length])
        
        return np.array(X), np.array(y)
    
    def fit(
        self,
        data: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        verbose: int = 0
    ) -> dict:
        """
        Train Transformer model
        
        Args:
            data: Time series data
            epochs: Number of epochs
            batch_size: Batch size
            validation_split: Validation split
            verbose: Verbosity
            
        Returns:
            Training history
        """
        if len(data) < self.sequence_length + 10:
            raise ValueError(f"Need at least {self.sequence_length + 10} data points")
        
        X, y = self.prepare_sequences(data)
        
        if np.isnan(X).any() or np.isnan(y).any():
            X = np.nan_to_num(X)
            y = np.nan_to_num(y)
        
        if len(X.shape) == 2:
            X = X.reshape(X.shape[0], X.shape[1], 1)
        
        num_features = X.shape[2]
        input_shape = (self.sequence_length, num_features)
        
        self.model = self.build_model(input_shape, num_features)
        
        callbacks = [
            EarlyStopping(patience=15, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=8)
        ]
        
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=verbose
        )
        
        self.is_fitted = True
        return history
    
    def predict(self, data: np.ndarray) -> np.ndarray:
        """
        Make prediction
        
        Args:
            data: Input data
            
        Returns:
            Prediction
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if len(data) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} data points")
        
        recent_data = data[-self.sequence_length:]
        
        if len(recent_data.shape) == 1:
            recent_data = recent_data.reshape(1, -1, 1)
        elif len(recent_data.shape) == 2:
            recent_data = recent_data.reshape(1, recent_data.shape[0], -1)
        
        prediction = self.model.predict(recent_data, verbose=0)
        return prediction[0]
    
    def predict_sequence(
        self,
        data: np.ndarray,
        steps: int = 5
    ) -> np.ndarray:
        """
        Predict multiple steps
        
        Args:
            data: Input data
            steps: Number of steps
            
        Returns:
            Predictions array
        """
        predictions = []
        current_data = data.copy()
        
        for _ in range(steps):
            pred = self.predict(current_data)
            predictions.append(pred[0])
            current_data = np.append(current_data[1:], pred[0])
        
        return np.array(predictions)


class HybridPredictor:
    """
    Ensemble of LSTM and Transformer models
    Combines strengths of both architectures
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 64,
        transformer_heads: int = 4,
        embed_dim: int = 64
    ):
        """
        Initialize hybrid predictor
        
        Args:
            sequence_length: Lookback window
            lstm_units: LSTM units
            transformer_heads: Transformer attention heads
            embed_dim: Transformer embedding dim
        """
        from ai_ml.lstm_forecast import LSTMPricePredictor
        
        self.lstm = LSTMPricePredictor(
            sequence_length=sequence_length,
            lstm_units=lstm_units
        )
        
        self.transformer = TransformerPricePredictor(
            sequence_length=sequence_length,
            num_heads=transformer_heads,
            embed_dim=embed_dim,
            ff_dim=embed_dim * 2
        )
        
        self.lstm_weight = 0.5
        self.transformer_weight = 0.5
    
    def fit(
        self,
        data: np.ndarray,
        epochs: int = 30,
        verbose: int = 0
    ):
        """
        Train both models
        
        Args:
            data: Training data
            epochs: Number of epochs
            verbose: Verbosity
        """
        print("Training LSTM model...")
        self.lstm.fit(data, epochs=epochs, verbose=verbose)
        
        print("Training Transformer model...")
        self.transformer.fit(data, epochs=epochs, verbose=verbose)
        
        print("Hybrid model trained successfully!")
    
    def predict(self, data: np.ndarray) -> float:
        """
        Make ensemble prediction
        
        Args:
            data: Input data
            
        Returns:
            Weighted prediction
        """
        lstm_pred = self.lstm.predict(data)[0]
        transformer_pred = self.transformer.predict(data)[0]
        
        return (
            self.lstm_weight * lstm_pred +
            self.transformer_weight * transformer_pred
        )
    
    def evaluate_ensemble(self, data: np.ndarray, test_size: int = 50) -> dict:
        """
        Evaluate ensemble performance
        
        Args:
            data: Test data
            test_size: Size of test set
            
        Returns:
            Evaluation metrics
        """
        predictions = []
        actuals = []
        
        test_data = data[:test_size]
        
        for i in range(self.lstm.sequence_length, len(test_data)):
            pred = self.predict(test_data[:i])
            actual = test_data[i]
            
            predictions.append(pred)
            actuals.append(actual)
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        mae = np.mean(np.abs(predictions - actuals))
        mse = np.mean((predictions - actuals) ** 2)
        rmse = np.sqrt(mse)
        
        mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
        
        return {
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'mape': mape
        }


if __name__ == "__main__":
    # Example usage
    if TENSORFLOW_AVAILABLE:
        print("Transformer Price Predictor Example")
        print("=" * 50)
        
        # Generate synthetic data
        np.random.seed(42)
        t = np.linspace(0, 100, 500)
        prices = 50000 + 10000 * np.sin(t/10) + \
                 5000 * np.cos(t/20) + \
                 np.random.normal(0, 500, len(t))
        
        # Create and train Transformer
        transformer = TransformerPricePredictor(
            sequence_length=50,
            num_heads=4,
            embed_dim=64,
            num_layers=2
        )
        history = transformer.fit(prices, epochs=20, verbose=1)
        
        # Make predictions
        prediction = transformer.predict(prices)
        print(f"\nCurrent Price: ${prices[-1]:.2f}")
        print(f"Predicted Price: ${prediction[0]:.2f}")
        print(f"Expected Change: {((prediction[0] - prices[-1]) / prices[-1] * 100):.2f}%")
        
        # Test hybrid model
        print("\nTesting Hybrid Predictor...")
        hybrid = HybridPredictor(sequence_length=50)
        hybrid.fit(prices[:400], epochs=15, verbose=0)
        
        metrics = hybrid.evaluate_ensemble(prices[400:], test_size=100)
        print("\nHybrid Model Performance:")
        print(f"MAE: {metrics['mae']:.2f}")
        print(f"RMSE: {metrics['rmse']:.2f}")
        print(f"MAPE: {metrics['mape']:.2f}%")
    else:
        print("TensorFlow is not available. Install with: pip install tensorflow")
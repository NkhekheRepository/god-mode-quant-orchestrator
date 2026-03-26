"""
LSTM-based Time Series Forecasting
Deep learning model for trading signal prediction
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import (
        LSTM, Dense, Dropout, Input, Bidirectional, 
        Attention, LayerNormalization, RepeatVector, TimeDistributed
    )
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. Install with: pip install tensorflow")

class LSTMPricePredictor:
    """
    LSTM Neural Network for Price Prediction
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
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required. Install with: pip install tensorflow")
        
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.bidirectional = bidirectional
        
        self.model = None
        self.scaler = None
        self.is_fitted = False
        
    def build_model(self, input_shape: tuple) -> Model:
        """
        Build LSTM model architecture
        
        Args:
            input_shape: Shape of input data (sequence_length, features)
            
        Returns:
            Compiled Keras model
        """
        inputs = Input(shape=input_shape)
        
        if self.bidirectional:
            x = Bidirectional(
                LSTM(self.lstm_units, return_sequences=True)
            )(inputs)
        else:
            x = LSTM(self.lstm_units, return_sequences=True)(inputs)
        
        x = Dropout(self.dropout_rate)(x)
        
        x = LSTM(self.lstm_units // 2, return_sequences=False)(x)
        x = Dropout(self.dropout_rate)(x)
        
        x = Dense(64, activation='relu')(x)
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
        Prepare sequences for LSTM training
        
        Args:
            data: Input time series data
            target: Target values (if None, use data shifted by 1)
            
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
        Train LSTM model
        
        Args:
            data: Time series data
            epochs: Number of training epochs
            batch_size: Batch size
            validation_split: Validation split ratio
            verbose: Verbosity level
            
        Returns:
            Training history
        """
        if len(data) < self.sequence_length + 10:
            raise ValueError(f"Need at least {self.sequence_length + 10} data points")
        
        X, y = self.prepare_sequences(data)
        
        if np.isnan(X).any() or np.isnan(y).any():
            X = np.nan_to_num(X)
            y = np.nan_to_num(y)
        
        input_shape = (X.shape[1], X.shape[2]) if len(X.shape) > 2 else (X.shape[1], 1)
        
        if len(X.shape) == 2:
            X = X.reshape(X.shape[0], X.shape[1], 1)
        
        self.model = self.build_model(input_shape)
        
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=5)
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
        Make predictions
        
        Args:
            data: Input time series data
            
        Returns:
            Predictions
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
        Predict multiple future steps
        
        Args:
            data: Input time series data
            steps: Number of steps to predict
            
        Returns:
            Array of predictions
        """
        predictions = []
        current_data = data.copy()
        
        for _ in range(steps):
            pred = self.predict(current_data)
            predictions.append(pred[0])
            current_data = np.append(current_data[1:], pred[0])
        
        return np.array(predictions)


class LSTMSignalGenerator:
    """
    LSTM-based trading signal generation
    Combines price prediction with trend analysis
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        lstm_units: int = 128,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize signal generator
        
        Args:
            sequence_length: Lookback window
            lstm_units: LSTM units
            confidence_threshold: Minimum prediction confidence
        """
        self.sequence_length = sequence_length
        self.model = LSTMPricePredictor(
            sequence_length=sequence_length,
            lstm_units=lstm_units
        )
        self.confidence_threshold = confidence_threshold
        self.recent_predictions = []
        self.max_history = 20
    
    def calculate_confidence(self, predictions: np.ndarray) -> float:
        """
        Calculate prediction confidence based on consistency
        
        Args:
            predictions: Recent predictions
            
        Returns:
            Confidence score [0, 1]
        """
        if len(predictions) < 2:
            return 0.5
        
        std = np.std(predictions)
        mean = np.mean(predictions)
        
        if mean == 0:
            return 0
        
        cv = std / abs(mean)
        confidence = max(0, 1 - cv * 2)
        
        return min(confidence, 1.0)
    
    def generate_signal(
        self,
        prices: np.ndarray,
        features: np.ndarray = None
    ) -> dict:
        """
        Generate trading signal
        
        Args:
            prices: Historical prices
            features: Additional features (volume, etc.)
            
        Returns:
            Signal dictionary
        """
        if len(prices) < self.sequence_length + 10:
            return {
                'signal': 0,
                'confidence': 0,
                'predicted_price': None,
                'expected_change': 0
            }
        
        if not self.model.is_fitted:
            self.model.fit(prices, verbose=0)
        
        current_price = prices[-1]
        predicted = self.model.predict(prices)[0]
        
        self.recent_predictions.append(predicted)
        if len(self.recent_predictions) > self.max_history:
            self.recent_predictions.pop(0)
        
        confidence = self.calculate_confidence(np.array(self.recent_predictions))
        
        expected_change = (predicted - current_price) / current_price
        
        signal = 0
        if confidence > self.confidence_threshold:
            if expected_change > 0.01:  # 1% increase
                signal = 1
            elif expected_change < -0.01:  # 1% decrease
                signal = -1
        
        return {
            'signal': signal,
            'confidence': confidence,
            'predicted_price': predicted,
            'expected_change': expected_change,
            'current_price': current_price
        }


if __name__ == "__main__":
    # Example usage
    if TENSORFLOW_AVAILABLE:
        print("LSTM Price Predictor Example")
        print("=" * 50)
        
        # Generate synthetic data
        np.random.seed(42)
        t = np.linspace(0, 100, 500)
        prices = 50000 + 10000 * np.sin(t/10) + \
                 5000 * np.cos(t/20) + \
                 np.random.normal(0, 500, len(t))
        
        # Create and train model
        predictor = LSTMPricePredictor(sequence_length=50, lstm_units=64)
        history = predictor.fit(prices, epochs=20, verbose=1)
        
        # Make predictions
        prediction = predictor.predict(prices)
        print(f"\nCurrent Price: ${prices[-1]:.2f}")
        print(f"Predicted Price: ${prediction[0]:.2f}")
        print(f"Expected Change: {((prediction[0] - prices[-1]) / prices[-1] * 100):.2f}%")
        
        # Generate trading signal
        signal_gen = LSTMSignalGenerator(sequence_length=50)
        signal = signal_gen.generate_signal(prices)
        print(f"\nTrading Signal: {signal['signal']} (1=Buy, -1=Sell, 0=Hold)")
        print(f"Confidence: {signal['confidence']:.2f}")
    else:
        print("TensorFlow is not available. Install with: pip install tensorflow")
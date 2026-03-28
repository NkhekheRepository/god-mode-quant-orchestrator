# Getting Started with AI/ML - GodMode Quant Orchestrator v2.0.0

## 🚀 Quick Start Guide

Welcome to the AI/ML module of the GodMode Quant Orchestrator! This guide will help you get started with machine learning models for cryptocurrency trading.

---

## 📋 Table of Contents

1. [Installation](#installation)
2. [Quick Start Example](#quick-start-example)
3. [Training Your First Model](#training-your-first-model)
4. [Making Predictions](#making-predictions)
5. [Using MLOps for Experiment Tracking](#using-mlops-for-experiment-tracking)
6. [Common ML Workflows](#common-ml-workflows)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Installation

### System Requirements

#### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 2GB free space
- **CPU**: Any modern multi-core processor

#### Recommended for Training Deep Learning Models
- **RAM**: 16GB or higher
- **GPU**: NVIDIA GPU with CUDA support (RTX 3060 or higher recommended)
- **Storage**: 10GB SSD free space
- **CUDA**: 11.8 or higher (for GPU acceleration)

### Step 1: Install Core Dependencies

```bash
# Navigate to the project directory
cd godmode-quant-orchestrator

# Install basic dependencies
pip install -r requirements.txt
```

### Step 2: Install ML Dependencies

#### Option A: Full ML Stack (Recommended for Training)

```bash
# Install ML-specific requirements
pip install -r ai_ml/requirements_ml.txt
```

#### Option B: Minimal ML Stack (For Inference Only)

```bash
# Install only what you need for running trained models
pip install tensorflow>=2.13.0 numpy>=1.24.0 pandas>=2.0.0
```

#### Option C: CPU-Only ML Stack (No GPU Available)

```bash
# Install CPU-optimized TensorFlow
pip install tensorflow-cpu>=2.13.0 numpy>=1.24.0 pandas>=2.0.0
```

### Step 3: Verify Installation

```bash
# Run verification script
python -c "
import tensorflow as tf
import numpy as np
import pandas as pd
print(f'TensorFlow: {tf.__version__}')
print(f'NumPy: {np.__version__}')
print(f'Pandas: {pd.__version__}')
print('All dependencies installed successfully!')
"
```

### Step 4: Test GPU Availability (Optional)

```bash
python -c "
import tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f'GPU detected: {gpus[0].name}')
else:
    print('No GPU detected. Will use CPU for training.')
"
```

---

## 🎯 Quick Start Example

Let's start with a simple example to get you up and running in minutes!

### Example 1: Basic Price Prediction

```python
"""
Quick Start Example: Basic Price Prediction
"""

from ai_ml import LSTMPricePredictor
import numpy as np

# Generate sample mock data (replace with real market data)
np.random.seed(42)
t = np.linspace(0, 100, 500)
prices = 50000 + 10000 * np.sin(t/10) + \
         5000 * np.cos(t/20) + \
         np.random.normal(0, 500, len(t))

print(f"Sample data generated: {len(prices)} price points")
print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}")

# Initialize the LSTM model
predictor = LSTMPricePredictor(
    sequence_length=60,  # Look back at last 60 candles
    lstm_units=128,      # 128 LSTM neurons
    dropout_rate=0.2     # Regularization to prevent overfitting
)

print("\nTraining model...")
print("This may take 1-2 minutes on CPU, 15-30 seconds on GPU")

# Train the model
history = predictor.fit(
    prices,
    epochs=20,           # Number of training passes
    batch_size=32,       # Number of samples per batch
    validation_split=0.2,# Use 20% for validation
    verbose=1            # Show progress bar
)

# Make a prediction
print("\nMaking prediction...")
prediction = predictor.predict(prices)

current_price = prices[-1]
predicted_price = prediction[0]
expected_change = ((predicted_price - current_price) / current_price) * 100

print(f"\n{'='*50}")
print(f"PREDICTION RESULTS")
print(f"{'='*50}")
print(f"Current Price:    ${current_price:.2f}")
print(f"Predicted Price:  ${predicted_price:.2f}")
print(f"Expected Change:  {expected_change:+.2f}%")
print(f"{'='*50}")

# Predict next 5 time steps
future_predictions = predictor.predict_sequence(prices, steps=5)
print(f"\nNext 5 predictions:")
for i, pred in enumerate(future_predictions, 1):
    print(f"  Step {i}: ${pred[0]:.2f}")
```

**Expected Output:**
```
Sample data generated: 500 price points
Price range: $35000.12 - $65000.87

Training model...
This may take 1-2 minutes on CPU, 15-30 seconds on GPU
Epoch 1/20
...
Epoch 20/20
13/13 [==============================] - 0s 4ms/step - loss: 0.0045 - mae: 0.0521

Making prediction...

==================================================
PREDICTION RESULTS
==================================================
Current Price:    $50023.45
Predicted Price:  $50156.78
Expected Change:  +0.27%
==================================================

Next 5 predictions:
  Step 1: $50156.78
  Step 2: $50289.12
  Step 3: $50421.56
  Step 4: $50553.89
  Step 5: $50686.23
```

---

## 🎓 Training Your First Model

### Data Preparation

#### Option 1: Using Historical CSV Data

```python
import pandas as pd
import numpy as np

# Load historical candle data
df = pd.read_csv('data/BTCUSDT_1h.csv')

print(f"Loaded {len(df)} candles")
print(df.head())

# Extract close prices
prices = df['close'].values

print(f"Price data shape: {prices.shape}")
print(f"Price range: ${prices.min():.2f} - ${prices.max():.2f}")
```

#### Option 2: Using Live Data from Exchange

```python
# Assuming you have access to exchange API
# This is a conceptual example - adapt to your data source

def fetch_historical_data(symbol, interval, limit=1000):
    """
    Fetch historical data from exchange
    Replace with your actual API call
    """
    # Example using ccxt library (install with: pip install ccxt)
    import ccxt

    exchange = ccxt.binance({
        'enableRateLimit': True,
    })

    ohlcv = exchange.fetch_ohlcv(
        symbol=symbol,
        timeframe=interval,
        limit=limit
    )

    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Fetch data
df = fetch_historical_data('BTC/USDT', '1h', 1000)
prices = df['close'].values
```

#### Option 3: Generating Synthetic Data (for Testing)

```python
def generate_synthetic_prices(n_points=1000, start_price=50000):
    """Generate synthetic price data for testing"""

    np.random.seed(42)

    # Create trend component
    t = np.linspace(0, 100, n_points)
    trend = 10000 * np.sin(t/10)

    # Add noise
    noise = np.random.normal(0, 500, n_points)

    # Combine
    prices = start_price + trend + noise

    # Ensure positive prices
    prices = np.maximum(prices, 1000)

    return prices

prices = generate_synthetic_prices(1000)
```

### Model Configuration

#### LSTM Model Configuration

```python
from ai_ml import LSTMPricePredictor

# Configuration for different market conditions
configs = {
    'conservative': {
        'sequence_length': 90,     # Longer lookback
        'lstm_units': 64,          # Smaller model
        'dropout_rate': 0.3,       # More regularization
        'learning_rate': 0.0001    # Slower learning
    },
    'balanced': {
        'sequence_length': 60,
        'lstm_units': 128,
        'dropout_rate': 0.2,
        'learning_rate': 0.001
    },
    'aggressive': {
        'sequence_length': 30,     # Shorter lookback
        'lstm_units': 256,         # Larger model
        'dropout_rate': 0.1,       # Less regularization
        'learning_rate': 0.001     # Normal learning rate
    }
}

# Choose configuration based on your strategy
config = configs['balanced']

# Initialize model
predictor = LSTMPricePredictor(
    sequence_length=config['sequence_length'],
    lstm_units=config['lstm_units'],
    dropout_rate=config['dropout_rate'],
    learning_rate=config['learning_rate']
)
```

#### Transformer Model Configuration

```python
from ai_ml import TransformerPricePredictor

# Initialize Transformer
predictor = TransformerPricePredictor(
    sequence_length=60,
    num_heads=4,           # Number of attention heads
    embed_dim=128,         # Embedding dimension
    ff_dim=256,            # Feed-forward dimension
    num_layers=3,          # Number of transformer blocks
    dropout_rate=0.1,
    learning_rate=0.0001
)
```

#### Hybrid Model Configuration

```python
from ai_ml import HybridPredictor

# Initialize Hybrid model
predictor = HybridPredictor(
    sequence_length=60,
    lstm_units=64,
    transformer_heads=4,
    embed_dim=64
)
```

### Training Workflow

```python
import matplotlib.pyplot as plt

def train_model(model, prices, model_name="Model"):
    """Complete training workflow"""

    print(f"\n{'='*60}")
    print(f"Training {model_name}")
    print(f"{'='*60}")

    # 1. Validate data
    min_required = model.sequence_length * 10  # Rule of thumb
    if len(prices) < min_required:
        raise ValueError(
            f"Not enough data. Need at least {min_required} points, "
            f"got {len(prices)}"
        )

    print(f"Training data size: {len(prices)} points")
    print(f"Sequence length: {model.sequence_length}")
    print(f"Model parameters: {model.sequence_length} LSTM units")

    # 2. Train model
    history = model.fit(
        prices,
        epochs=50,
        batch_size=32,
        validation_split=0.2,
        verbose=1
    )

    # 3. Plot training history
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title(f'{model_name} - Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['mae'], label='Training MAE')
    plt.plot(history.history['val_mae'], label='Validation MAE')
    plt.title(f'{model_name} - Training MAE')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()

    plt.tight_layout()
    plt.savefig(f'{model_name.lower()}_training_history.png')
    print(f"\nTraining history saved to {model_name.lower()}_training_history.png")

    # 4. Print summary
    final_train_loss = history.history['loss'][-1]
    final_val_loss = history.history['val_loss'][-1]
    final_train_mae = history.history['mae'][-1]
    final_val_mae = history.history['val_mae'][-1]

    print(f"\n{'='*60}")
    print(f"TRAINING SUMMARY")
    print(f"{'='*60}")
    print(f"Final Training Loss:   {final_train_loss:.4f}")
    print(f"Final Validation Loss: {final_val_loss:.4f}")
    print(f"Final Training MAE:    {final_train_mae:.2f}")
    print(f"Final Validation MAE:  {final_val_mae:.2f}")
    print(f"{'='*60}")

    return history
```

### Save and Load Trained Model

```python
# Save model using TensorFlow's native format
model.model.save('models/btc_lstm_predictor.keras')

# Load model later
from tensorflow import keras
loaded_model = keras.models.load_model('models/btc_lstm_predictor.keras')

# Or use MLOps for version tracking (recommended)
from ai_ml import MLOpsManager

mlops = MLOpsManager(experiment_name="btc_prediction")
mlops.start_run(run_name="lstm_model_v1")
mlops.log_model(model.model, model_type='keras')
mlops.end_run()
```

---

## 🔮 Making Predictions

### Single Prediction

```python
from ai_ml import LSTMPricePredictor
import numpy as np

# Load or train model
predictor = LSTMPricePredictor(sequence_length=60)
predictor.fit(prices, epochs=50, verbose=0)

# Make prediction
prediction = predictor.predict(prices)

current_price = prices[-1]
predicted_price = prediction[0]
confidence = max(0, 1 - abs(predicted_price - current_price) / current_price)

print(f"Current Price: ${current_price:.2f}")
print(f"Predicted Price: ${predicted_price:.2f}")
print(f"Expected Change: {((predicted_price - current_price) / current_price) * 100:+.2f}%")
print(f"Confidence: {confidence:.2%}")
```

### Multiple Step Predictions

```python
# Predict next 10 time steps
future_prices = predictor.predict_sequence(prices, steps=10)

print("\nFuture Price Predictions:")
for i, price in enumerate(future_prices, 1):
    change = ((price - current_price) / current_price) * 100
    print(f"Step {i:2d}: ${price[0]:8.2f} ({change:+6.2f}%)")

# Plot predictions
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))

# Historical prices
plt.plot(range(len(prices[-120:])), prices[-120:],
         label='Historical', linewidth=2)

# Predictions
pred_start = len(prices[-120:])
plt.plot(range(pred_start, pred_start + len(future_prices)),
         future_prices,
         label='Predicted', linewidth=2, linestyle='--')

plt.axvline(pred_start, color='red', linestyle=':', label='Prediction Start')
plt.xlabel('Time')
plt.ylabel('Price ($)')
plt.title('BTC Price Forecast')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('price_forecast.png')
```

### Generating Trading Signals

```python
from ai_ml import LSTMSignalGenerator

# Initialize signal generator
signal_gen = LSTMSignalGenerator(
    sequence_length=60,
    lstm_units=128,
    confidence_threshold=0.7  # Only trade when confidence > 70%
)

# Generate signal
signal_result = signal_gen.generate_signal(prices)

# Interpret signal
signal = signal_result['signal']
signal_text = {1: 'BUY', -1: 'SELL', 0: 'HOLD'}[signal]

print(f"\nTRADING SIGNAL")
print(f"{'='*40}")
print(f"Signal:           {signal_text}")
print(f"Confidence:       {signal_result['confidence']:.2%}")
print(f"Current Price:    ${signal_result['current_price']:.2f}")
print(f"Predicted Price:  ${signal_result['predicted_price']:.2f}")
print(f"Expected Change:  {signal_result['expected_change']*100:+.2f}%")
print(f"{'='*40}")

# Trade recommendation
if signal_result['confidence'] > 0.7:
    if signal == 1:
        print("RECOMMENDATION: Consider BUY entry")
        print(f"Entry price: ${signal_result['current_price']:.2f}")
        print(f"Target: ${signal_result['predicted_price']:.2f}")
    elif signal == -1:
        print("RECOMMENDATION: Consider SELL entry")
        print(f"Entry price: ${signal_result['current_price']:.2f}")
        print(f"Target: ${signal_result['predicted_price']:.2f}")
    else:
        print("RECOMMENDATION: Hold position")
else:
    print("RECOMMENDATION: No trade - confidence too low")
```

### Prediction with Multiple Features

```python
# Prepare multi-feature data
# Features: [close_price, volume, rsi]

def prepare_features(df):
    """Prepare multi-feature input"""

    # Calculate RSI (Relative Strength Index)
    def calculate_rsi(prices, period=14):
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        return 100 - (100 / (1 + rs))

    features = []

    for i in range(len(df)):
        close = df['close'].iloc[i]
        volume = df['volume'].iloc[i]
        rsi = calculate_rsi(df['close'].iloc[max(0, i-14):i+1].values)
        features.append([close, volume, rsi])

    return np.array(features)

# Load data and prepare features
df = pd.read_csv('data/BTCUSDT_1h.csv')
features = prepare_features(df)

print(f"Feature shape: {features.shape}")
print(f"Features per candle: close_price, volume, rsi")

# Train with multi-feature data
predictor = TransformerPricePredictor(
    sequence_length=60,
    embed_dim=128
)

history = predictor.fit(
    features,
    epochs=50,
    verbose=1
)
```

---

## 📊 Using MLOps for Experiment Tracking

MLflow is integrated into the AI/ML module for comprehensive experiment tracking.

### Initialize MLOps Manager

```python
from ai_ml import MLOpsManager, ExperimentTracker

# Initialize MLOps
mlops = MLOpsManager(
    tracking_uri="file:///home/ubuntu/godmode-quant-orchestrator/mlruns",
    experiment_name="btc_prediction_v2"
)

# Create experiment tracker
tracker = ExperimentTracker(mlops)
```

### Track Training Experiment

```python
# Start experiment
tracker.start_experiment(
    strategy_name="lstm_price_prediction",
    symbol="BTCUSDT",
    parameters={
        'sequence_length': 60,
        'lstm_units': 128,
        'dropout_rate': 0.2,
        'learning_rate': 0.001,
        'epochs': 50,
        'batch_size': 32
    }
)

# Train model
predictor = LSTMPricePredictor(
    sequence_length=60,
    lstm_units=128
)

history = predictor.fit(
    prices,
    epochs=50,
    batch_size=32,
    verbose=0
)

# Log metrics
final_metrics = {
    'train_loss': history.history['loss'][-1],
    'val_loss': history.history['val_loss'][-1],
    'train_mae': history.history['mae'][-1],
    'val_mae': history.history['val_mae'][-1]
}

mlops.log_metrics(final_metrics)

# Log model
mlops.log_model(
    model=predictor.model,
    model_type='keras',
    artifact_path='lstm_model'
)

# Register model for production
model_version = mlops.register_model(
    model_name='btc_lstm_predictor',
    artifact_path='lstm_model'
)

print(f"Model registered with version: {model_version}")

# End experiment
tracker.end_experiment()
```

### Perform A/B Testing

```python
from ai_ml import LSTMPricePredictor, TransformerPricePredictor

# Experiment 1: LSTM
tracker.start_experiment(
    strategy_name="lstm_price_prediction",
    symbol="BTCUSDT",
    parameters={'model_type': 'lstm', 'epochs': 50}
)

lstm = LSTMPricePredictor(sequence_length=60)
lstm.fit(prices, epochs=50, verbose=0)

lstm_preds = []
for i in range(400, 500):
    pred = lstm.predict(prices[:i])
    actual = prices[i]
    lstm_preds.append(abs(pred - actual))

lstm_mae = np.mean(lstm_preds)
mlops.log_metrics({'test_mae': lstm_mae})
mlops.log_model(lstm.model, 'keras', 'lstm_model')
 tracker.end_experiment()

# Experiment 2: Transformer
tracker.start_experiment(
    strategy_name="transformer_price_prediction",
    symbol="BTCUSDT",
    parameters={'model_type': 'transformer', 'epochs': 50}
)

transformer = TransformerPricePredictor(sequence_length=60)
transformer.fit(prices, epochs=50, verbose=0)

trans_preds = []
for i in range(400, 500):
    pred = transformer.predict(prices[:i])
    actual = prices[i]
    trans_preds.append(abs(pred - actual))

trans_mae = np.mean(trans_preds)
mlops.log_metrics({'test_mae': trans_mae})
mlops.log_model(transformer.model, 'keras', 'transformer_model')
tracker.end_experiment()

print(f"\nA/B Test Results:")
print(f"LSTM MAE:      {lstm_mae:.2f}")
print(f"Transformer MAE: {trans_mae:.2f}")
print(f"Winner: {'LSTM' if lstm_mae < trans_mae else 'Transformer'}")
```

### Monitor Model Performance Over Time

```python
from ai_ml import ModelPerformanceTracker

# Initialize performance tracker
tracker = ModelPerformanceTracker(
    window_size=100,
    drift_threshold=0.2
)

# Simulate ongoing monitoring
dates = pd.date_range(start='2024-01-01', periods=100, freq='H')

for i, (date, actual) in enumerate(zip(dates, prices[400:500])):
    # Make prediction
    pred = predictor.predict(prices[:400+i])

    # Add to tracker
    tracker.add_prediction(
        prediction=pred[0],
        actual=actual,
        timestamp=date
    )

    # Check for drift
    metrics = tracker.get_current_metrics()
    print(f"{date.strftime('%Y-%m-%d %H:%M')} - "
          f"MAE: {metrics.get('mae', 0):.2f} - "
          f"Drift: {'YES' if tracker.drift_detected else 'NO'}")

    if tracker.drift_detected:
        print("⚠️  WARNING: Model drift detected!")
        print("Consider retraining the model.")
        break
```

---

## 🔄 Common ML Workflows

### Workflow 1: Daily Model Retraining

```python
import schedule
import time

def daily_retrain_job():
    """Retrain model daily with latest data"""

    print(f"\n[{datetime.now()}] Starting daily model retraining...")

    # 1. Fetch latest data
    latest_data = fetch_historical_data('BTC/USDT', '1h', 2000)

    # 2. Train new model
    predictor = LSTMPricePredictor(sequence_length=60)
    predictor.fit(latest_data['close'].values, epochs=50, verbose=0)

    # 3. Evaluate on test set
    test_mae = evaluate_model(predictor, latest_data[-200:])

    # 4. Save if performance is good
    if test_mae < 500:  # Threshold
        predictor.model.save('models/btc_predictor_latest.keras')
        print(f"Model saved with MAE: {test_mae:.2f}")
    else:
        print(f"Model performance too poor (MAE: {test_mae:.2f}), not saving")

    # 5. Log to MLflow
    mlops.start_run(run_name="daily_retrain")
    mlops.log_metrics({'test_mae': test_mae})
    mlops.log_model(predictor.model, 'keras')
    mlops.end_run()

# Schedule daily job at 2 AM
schedule.every().day.at("02:00").do(daily_retrain_job)

print("Daily retraining scheduled for 2:00 AM")
```

### Workflow 2: Real-Time Inference Service

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load model at startup
predictor = LSTMPricePredictor(sequence_length=60)
predictor.model = keras.models.load_model('models/btc_predictor_latest.keras')

@app.route('/predict', methods=['POST'])
def predict():
    """Prediction endpoint"""

    data = request.json
    prices = np.array(data['prices'])

    # Validate input
    if len(prices) < predictor.sequence_length:
        return jsonify({
            'error': f'Need at least {predictor.sequence_length} price points'
        }), 400

    try:
        # Make prediction
        prediction = predictor.predict(prices[-predictor.sequence_length*2:])

        # Calculate confidence
        current = prices[-1]
        predicted = prediction[0]
        confidence = max(0, 1 - abs(predicted - current) / current)

        return jsonify({
            'prediction': float(predicted),
            'current_price': float(current),
            'expected_change_pct': float((predicted - current) / current * 100),
            'confidence': float(confidence)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### Workflow 3: Ensemble Model with Voting

```python
def ensemble_predict(prices):
    """Combine predictions from multiple models"""

    # Initialize models
    lstm = LSTMPricePredictor(sequence_length=60)
    transformer = TransformerPricePredictor(sequence_length=60)

    # Train all models
    lstm.fit(prices[:800], epochs=50, verbose=0)
    transformer.fit(prices[:800], epochs=50, verbose=0)

    # Get predictions
    lstm_pred = lstm.predict(prices)[0]
    trans_pred = transformer.predict(prices)[0]

    # Weighted average (Transformer typically better long-term)
    weighted_pred = 0.4 * lstm_pred + 0.6 * trans_pred

    # Calculate confidence based on agreement
    pred_diff = abs(lstm_pred - trans_pred)
    agreement = max(0, 1 - pred_diff / prices[-1])
    confidence = max(lstm_pred, trans_pred) if agreement > 0.8 else weighted_pred

    return {
        'ensemble_prediction': weighted_pred,
        'lstm_prediction': lstm_pred,
        'transformer_prediction': trans_pred,
        'agreement_score': agreement,
        'confidence': confidence
    }

# Use ensemble
result = ensemble_predict(prices)
print(f"Ensemble prediction: ${result['ensemble_prediction']:.2f}")
print(f"Agreement: {result['agreement_score']:.2%}")
```

### Workflow 4: Backtesting with ML Predictions

```python
def backtest_ml_strategy(prices, predictor, initial_capital=10000):
    """Backtest ML-based trading strategy"""

    position = 0  # 0=none, 1=long, -1=short
    capital = initial_capital
    holdings = 0
    trades = []
    pnl_history = []

    for i in range(predictor.sequence_length, len(prices)):
        current_price = prices[i]
        historical_prices = prices[:i]

        # Get prediction
        pred = predictor.predict(historical_prices)[0]
        expected_return = (pred - current_price) / current_price

        # Trading logic
        if position == 0:
            # No position, consider entering
            if expected_return > 0.01:  # Predict >1% gain
                # Go long
                holdings = capital / current_price
                position = 1
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'time': i
                })
            elif expected_return < -0.01:  # Predict >1% loss
                # Go short
                holdings = -capital / current_price
                position = -1
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'time': i
                })
        elif position == 1:
            # Long position, consider closing
            if expected_return < -0.005:  # Predict <0.5% gain or loss
                # Close long
                capital = holdings * current_price
                holdings = 0
                position = 0
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'time': i
                })
        elif position == -1:
            # Short position, consider closing
            if expected_return > 0.005:
                # Close short
                capital = -holdings * current_price
                holdings = 0
                position = 0
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'time': i
                })

        # Update P&L
        if position == 1:
            current_value = holdings * current_price
        elif position == -1:
            current_value = -holdings * current_price + capital
        else:
            current_value = capital

        pnl_history.append((current_value - initial_capital) / initial_capital * 100)

    # Calculate metrics
    final_pnl = (capital - initial_capital) / initial_capital * 100
    win_trades = sum(1 for i in range(0, len(trades)-1, 2)
                     if trades[i+1]['price'] > trades[i]['price'])
    win_rate = win_trades / (len(trades) // 2) if len(trades) > 0 else 0

    max_drawdown = -min(pnl_history)

    return {
        'final_pnl_pct': final_pnl,
        'total_trades': len(trades),
        'win_rate': win_rate,
        'max_drawdown_pct': max_drawdown,
        'pnl_history': pnl_history,
        'trades': trades
    }

# Run backtest
predictor = LSTMPricePredictor(sequence_length=60)
predictor.fit(prices[:800], epochs=50, verbose=0)

results = backtest_ml_strategy(prices[800:], predictor)

print(f"\nBacktest Results:")
print(f"Final P&L: {results['final_pnl_pct']:+.2f}%")
print(f"Total Trades: {results['total_trades']}")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
```

---

## ⚠️ Troubleshooting

### Common Issues and Solutions

#### Issue 1: TensorFlow Import Error

**Problem:**
```
ImportError: No module named 'tensorflow'
```

**Solution:**
```bash
pip install tensorflow>=2.13.0
```

#### Issue 2: GPU Not Detected

**Problem:**
```
No GPU detected. Will use CPU for training.
```

**Solution:**
```bash
# Install CUDA toolkit (NVIDIA GPU)
# Visit: https://developer.nvidia.com/cuda-downloads

# Install cuDNN
# Visit: https://developer.nvidia.com/cudnn

# Verify GPU detection
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

#### Issue 3: Out of Memory During Training

**Problem:**
```
ResourceExhaustedError: OOM when allocating tensor
```

**Solution:**
```python
# Reduce batch size
predictor.fit(prices, epochs=50, batch_size=16)  # Reduce from 32

# Or reduce model size
predictor = LSTMPricePredictor(
    sequence_length=30,  # Reduce from 60
    lstm_units=64       # Reduce from 128
)

# Clear GPU memory before training
import tensorflow as tf
tf.keras.backend.clear_session()
```

#### Issue 4: Model Overfitting

**Problem:**
Training loss keeps decreasing but validation loss increases.

**Solution:**
```python
# Increase dropout rate
predictor = LSTMPricePredictor(
    sequence_length=60,
    lstm_units=128,
    dropout_rate=0.3  # Increase from 0.2
)

# Add more training data
# Collect more historical candles

# Reduce model complexity
predictor = LSTMPricePredictor(
    sequence_length=60,
    lstm_units=64  # Reduce from 128
)
```

#### Issue 5: Inference Too Slow

**Problem:**
Predictions taking too long for real-time trading.

**Solution:**
```python
# Use simpler model
from ai_ml.time_series_forecast import TimeSeriesForecaster
forecaster = TimeSeriesForecaster(model_type='random_forest')
forecaster.fit(prices, lookback=10)
pred = forecaster.predict(prices, lookback=10)  # 100x faster

# Or use model quantization (advanced)
# Requires TensorFlow Lite
```

#### Issue 6: Poor Prediction Accuracy

**Problem:**
Model MAE consistently high (>2%).

**Solution:**
```python
# Try different sequence length
predictor = LSTMPricePredictor(sequence_length=90)  # Increase lookback

# Try Transformer for long-term patterns
from ai_ml import TransformerPricePredictor
predictor = TransformerPricePredictor(sequence_length=60)

# Try Hybrid model
from ai_ml import HybridPredictor
predictor = HybridPredictor(sequence_length=60)

# Add more features
features = prepare_multi_feature_data(df)
predictor.fit(features, epochs=50)

# Hyperparameter tuning
# See MODELS.md - Hyperparameter Tuning section
```

#### Issue 7: MLflow Tracking Not Working

**Problem:**
Experiments not being tracked.

**Solution:**
```python
# Verify MLflow is installed
pip install mlflow>=2.7.0

# Check tracking URI
import os
os.environ['MLFLOW_TRACKING_URI'] = 'file:///path/to/mlruns'

# Initialize with full path
mlops = MLOpsManager(
    tracking_uri='file:///absolute/path/to/mlruns',
    experiment_name='my_experiment'
)

# View experiments
# Run: mlflow ui
# Then open: http://localhost:5000
```

### Debug Tips

#### Enable Verbose Logging
```python
import logging

# Set TensorFlow logging level
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=all, 1=warning, 2=error

# Set Python logging
logging.basicConfig(level=logging.INFO)
```

#### Validate Data Before Training
```python
def validate_data(prices, model):
    """Validate data before training"""

    print(f"Data validation:")
    print(f"  Total points: {len(prices)}")
    print(f"  Required: {model.sequence_length * 10}")
    print(f"  NaN values: {np.isnan(prices).sum()}")
    print(f"  Inf values: {np.isinf(prices).sum()}")
    print(f"  Min value: ${prices.min():.2f}")
    print(f"  Max value: ${prices.max():.2f}")
    print(f"  Mean value: ${prices.mean():.2f}")

    if len(prices) < model.sequence_length * 10:
        raise ValueError("Not enough data points")

    if np.isnan(prices).any() or np.isinf(prices).any():
        raise ValueError("Data contains NaN or Inf values")

    print("  ✓ Data validation passed")
```

### Performance Optimization Tips

#### 1. Use GPU When Available
```python
import tensorflow as tf

# Configure GPU memory growth
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print("GPU memory growth enabled")
    except RuntimeError as e:
        print(e)
```

#### 2. Increase Batch Size for GPU
```python
# GPU can handle larger batches
predictor.fit(prices, epochs=50, batch_size=64 or 128)
```

#### 3. Use Mixed Precision (Advanced)
```python
# Requires compatible GPU
policy = tf.keras.mixed_precision.Policy('mixed_float16')
tf.keras.mixed_precision.set_global_policy(policy)
```

#### 4. Cache Preprocessed Data
```python
import pickle

# Save preprocessed data
with open('data/preprocessed.pkl', 'wb') as f:
    pickle.dump((X_train, y_train, X_val, y_val), f)

# Load preprocessed data
with open('data/preprocessed.pkl', 'rb') as f:
    X_train, y_train, X_val, y_val = pickle.load(f)
```

---

## 📚 Next Steps

1. **Read [MODELS.md](MODELS.md)** - Learn about all available models
2. **Check [EXAMPLES.md](EXAMPLES.md)** - Explore practical examples
3. **Review Model Performance** - Understand benchmarks and expectations
4. **Experiment with Data** - Try different cryptocurrencies and timeframes
5. **Production Deployment** - Learn about deploying models to production

---

## 🆘 Getting Help

If you encounter issues not covered in this guide:

1. Check the [MODELS.md](MODELS.md) documentation
2. Review the [EXAMPLES.md](EXAMPLES.md) for working code
3. Search existing issues on GitHub
4. Open a new issue with:
   - Your Python version
   - TensorFlow version
   - Full error message
   - Minimal reproducible example

---

**Last Updated**: March 26, 2026
**Version**: 2.0.0
**GodMode Quant Orchestrator**
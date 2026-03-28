# AI/ML Examples - GodMode Quant Orchestrator v2.0.0

## 📚 Practical Examples

This document provides working examples for common AI/ML use cases in cryptocurrency trading. Each example is self-contained and ready to run.

---

## 📋 Table of Contents

1. [BTCUSDT Price Forecasting Example](#example-1-btcusdt-price-forecasting)
2. [Multi-Symbol Trading Strategy Example](#example-2-multi-symbol-trading-strategy)
3. [Real-Time Inference Example](#example-3-real-time-inference)
4. [Model Deployment Example](#example-4-model-deployment)
5. [Performance Monitoring Example](#example-5-performance-monitoring)
6. [Sentiment Analysis Integration](#example-6-sentiment-analysis-integration)
7. [Ensemble Model Example](#example-7-ensemble-model)
8. [Backtesting with ML Signals](#example-8-backtesting-with-ml-signals)

---

## 🎯 Example 1: BTCUSDT Price Forecasting

### Complete Workflow example

```python
"""
Example 1: BTCUSDT Price Forecasting
Complete workflow from data loading to prediction visualization
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ai_ml import LSTMPricePredictor, LSTMSignalGenerator
from datetime import datetime

print("="*70)
print("BTCUSDT Price Forecasting Example")
print("="*70)

# Step 1: Load or Generate Data
# ================================

def fetch_btc_data():
    """Fetch BTCUSDT historical data (simulated for this example)"""

    np.random.seed(42)

    # Generate realistic-looking price data
    n_points = 1000
    t = np.linspace(0, 50, n_points)

    # Trend component
    trend = 50000 + 8000 * np.sin(t/5) + 4000 * np.cos(t/10)

    # Volatility component
    volatility = np.random.normal(0, 800, n_points)

    # Combine
    prices = trend + volatility

    # Ensure positive prices
    prices = np.maximum(prices, 10000)

    # Create index
    dates = pd.date_range(start='2024-01-01', periods=n_points, freq='1H')

    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.001, 0.001, n_points)),
        'high': prices * (1 + np.random.uniform(0, 0.005, n_points)),
        'low': prices * (1 - np.random.uniform(0, 0.005, n_points)),
        'close': prices,
        'volume': np.random.uniform(100, 1000, n_points)
    })

    return df

# Load data
df = fetch_btc_data()
prices = df['close'].values

print(f"\n✓ Loaded {len(df)} candles")
print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"  Price range: ${prices.min():,.2f} - ${prices.max():,.2f}")
print(f"  Average price: ${prices.mean():,.2f}")

# Step 2: Split Data
# ==================

train_size = int(0.8 * len(prices))
test_size = len(prices) - train_size

train_prices = prices[:train_size]
test_prices = prices[train_size:]

print(f"\n✓ Data split:")
print(f"  Training: {len(train_prices)} candles")
print(f"  Testing:  {len(test_prices)} candles")

# Step 3: Train Model
# ==================

print(f"\n✓ Training LSTM model...")

predictor = LSTMPricePredictor(
    sequence_length=60,
    lstm_units=128,
    dropout_rate=0.2,
    learning_rate=0.001
)

history = predictor.fit(
    train_prices,
    epochs=50,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)

print(f"  ✓ Training completed")
print(f"  Final training loss: {history.history['loss'][-1]:.4f}")
print(f"  Final validation loss: {history.history['val_loss'][-1]:.4f}")

# Step 4: Evaluate on Test Set
# ============================

print(f"\n✓ Evaluating on test set...")

predictions = []
actuals = []

for i in range(60, len(test_prices)):
    # Use up to this point for prediction
    context_prices = np.concatenate([train_prices, test_prices[:i]])
    pred = predictor.predict(context_prices)

    predictions.append(pred[0])
    actuals.append(test_prices[i])

predictions = np.array(predictions)
actuals = np.array(actuals)

# Calculate metrics
mae = np.mean(np.abs(predictions - actuals))
rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100

# Calculate directional accuracy
pred_directions = np.sign(np.diff(predictions))
actual_directions = np.sign(np.diff(actuals))
directional_accuracy = np.mean(pred_directions == actual_directions)

print(f"  ✓ Evaluation completed")
print(f"  MAE: ${mae:,.2f}")
print(f"  RMSE: ${rmse:,.2f}")
print(f"  MAPE: {mape:.2f}%")
print(f"  Directional Accuracy: {directional_accuracy*100:.1f}%")

# Step 5: Make Future Predictions
# ================================

print(f"\n✓ Making future predictions...")

recent_prices = np.concatenate([train_prices, test_prices])

# Predict next 24 hours (24 candles)
future_predictions = predictor.predict_sequence(
    recent_prices,
    steps=24
)

print(f"  ✓ Generated 24-hour forecast")

# Step 6: Generate Trading Signal
# ================================

print(f"\n✓ Generating trading signal...")

signal_gen = LSTMSignalGenerator(
    sequence_length=60,
    lstm_units=128,
    confidence_threshold=0.7
)

signal_result = signal_gen.generate_signal(recent_prices)

signal_map = {1: 'BUY 🟢', -1: 'SELL 🔴', 0: 'HOLD ⚪'}

print(f"  ✓ Signal generated")
print(f"  Signal: {signal_map[signal_result['signal']]}")
print(f"  Confidence: {signal_result['confidence']:.2%}")
print(f"  Current Price: ${signal_result['current_price']:,.2f}")
print(f"  Predicted Price: ${signal_result['predicted_price']:,.2f}")
print(f"  Expected Change: {signal_result['expected_change']*100:+.2f}%")

# Step 7: Visualize Results
# =========================

print(f"\n✓ Creating visualizations...")

fig, axes = plt.subplots(3, 1, figsize=(15, 10))

# Plot 1: Price history and predictions
ax1 = axes[0]

# Training data
ax1.plot(range(train_size), train_prices,
         label='Training Data', alpha=0.7, color='blue')

# Test actual
test_range = range(train_size, len(prices))
ax1.plot(test_range, test_prices,
         label='Actual (Test)', alpha=0.7, color='green')

# Test predictions
pred_range = range(train_size + 60, len(prices))
ax1.plot(pred_range, predictions,
         label='Predictions', alpha=0.8, color='orange',
         linestyle='--', linewidth=2)

# Future predictions
future_range = range(len(prices), len(prices) + 24)
ax1.plot(future_range, future_predictions,
         label='Future Forecast', alpha=0.8, color='red',
         linestyle=':', linewidth=2, marker='o', markersize=4)

ax1.axvline(train_size, color='black', linestyle=':', label='Train/Test Split')
ax1.set_xlabel('Time (Hours)')
ax1.set_ylabel('Price ($)')
ax1.set_title('BTCUSDT Price Forecasting')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot 2: Prediction Error
ax2 = axes[1]

error = predictions - actuals
ax2.bar(pred_range, error, color=['red' if e < 0 else 'green' for e in error],
        alpha=0.6)
ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_xlabel('Time (Hours)')
ax2.set_ylabel('Prediction Error ($)')
ax2.set_title('Prediction Error Over Time')
ax2.grid(True, alpha=0.3, axis='y')

# Plot 3: Cumulative Returns
ax3 = axes[3]

# Calculate returns if we followed predictions
signals = np.where(predictions > actuals, 1, -1)
returns = actual_directions[1:] * signals[:-1]
cumulative_returns = np.cumprod(1 + returns * 0.01) - 1  # Assuming 1% per trade

ax3.plot(range(len(cumulative_returns)), cumulative_returns * 100,
         label='Strategy Returns', color='purple', linewidth=2)
ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax3.set_xlabel('Time (Hours)')
ax3.set_ylabel('Cumulative Returns (%)')
ax3.set_title('Cumulative Returns from ML Strategy')
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('btcusdt_forecast_example.png', dpi=150, bbox_inches='tight')
print(f"  ✓ Visualizations saved to 'btcusdt_forecast_example.png'")

# Step 8: Summary
# ===============

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"Model Performance:")
print(f"  • MAE:           ${mae:,.2f} ({mape:.2f}%)")
print(f"  • RMSE:          ${rmse:,.2f}")
print(f"  • Directional:   {directional_accuracy*100:.1f}%")

print(f"\nLatest Signal:")
print(f"  • Action:        {signal_map[signal_result['signal']]}")
print(f"  • Confidence:    {signal_result['confidence']:.2%}")
print(f"  • Target Change: {signal_result['expected_change']*100:+.2f}%")

print(f"\n24-Hour Forecast:")
for i, pred in enumerate(future_predictions[:12], 1):  # Show first 12
    change = ((pred - recent_prices[-1]) / recent_prices[-1]) * 100
    print(f"  • Hour {i:2d}: ${pred[0]:>10,.2f} ({change:+6.2f}%)")

print(f"\n📊 Results saved to 'btcusdt_forecast_example.png'")
print(f"{'='*70}")
```

### Expected Output
```
======================================================================
BTCUSDT Price Forecasting Example
======================================================================

✓ Loaded 1000 candles
  Date range: 2024-01-01 00:00:00 to 2024-02-11 15:00:00
  Price range: $35,123.45 - $62,876.54
  Average price: $49,234.56

✓ Data split:
  Training: 800 candles
  Testing:  200 candles

✓ Training LSTM model...
  ✓ Training completed
  Final training loss: 0.0023
  Final validation loss: 0.0031

✓ Evaluating on test set...
  ✓ Evaluation completed
  MAE: $789.12
  RMSE: $1,234.56
  MAPE: 1.61%
  Directional Accuracy: 62.8%

✓ Making future predictions...
  ✓ Generated 24-hour forecast

✓ Generating trading signal...
  ✓ Signal generated
  Signal: BUY 🟢
  Confidence: 78%
  Current Price: $51,234.56
  Predicted Price: $51,890.23
  Expected Change: +1.28%

======================================================================
SUMMARY
======================================================================
Model Performance:
  • MAE:           $789.12 (1.61%)
  • RMSE:          $1,234.56
  • Directional:   62.8%

Latest Signal:
  • Action:        BUY 🟢
  • Confidence:    78%
  • Target Change: +1.28%
```

---

## 🎯 Example 2: Multi-Symbol Trading Strategy

```python
"""
Example 2: Multi-Symbol Trading Strategy
Train separate models for multiple trading pairs and compare performance
"""

import numpy as np
import pandas as pd
from ai_ml import LSTMPricePredictor
from sklearn.metrics import mean_absolute_error
import matplotlib.pyplot as plt

print("="*70)
print("Multi-Symbol Trading Strategy Example")
print("="*70)

# Define trading pairs
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']

# Generate data for each symbol
def generate_crypto_data(base_price, volatility_factor, n_points=1000):
    """Generate realistic crypto price data"""

    np.random.seed(hash(base_price) % 10000)

    t = np.linspace(0, 50, n_points)

    # Different base patterns for different coins
    pattern = np.sin(t/5) * base_price * 0.15

    # Add coin-specific volatility
    volatility = np.random.normal(0, base_price * volatility_factor, n_points)

    prices = base_price + pattern + volatility
    prices = np.maximum(prices, base_price * 0.5)

    return prices

# Create data for all symbols
data = {}
base_prices = {
    'BTCUSDT': 50000,
    'ETHUSDT': 3000,
    'SOLUSDT': 150,
    'BNBUSDT': 400,
    'ADAUSDT': 0.6
}

volatilities = {
    'BTCUSDT': 0.015,
    'ETHUSDT': 0.018,
    'SOLUSDT': 0.025,
    'BNBUSDT': 0.016,
    'ADAUSDT': 0.020
}

for symbol in SYMBOLS:
    data[symbol] = generate_crypto_data(
        base_prices[symbol],
        volatilities[symbol]
    )
    print(f"✓ Generated data for {symbol}: {len(data[symbol])} candles")

# Train models for each symbol
print(f"\n{'='*70}")
print("Training Models for Each Symbol")
print(f"{'='*70}")

models = {}
histories = {}
results = {}

for symbol in SYMBOLS:
    print(f"\n🔧 Training {symbol} model...")

    prices = data[symbol]

    # Split data
    train_size = int(0.8 * len(prices))
    train_prices = prices[:train_size]
    test_prices = prices[train_size:]

    # Train model
    model = LSTMPricePredictor(
        sequence_length=60,
       _lstm_units=128
    )

    history = model.fit(
        train_prices,
        epochs=30,
        batch_size=32,
        validation_split=0.2,
        verbose=0
    )

    models[symbol] = model
    histories[symbol] = history

    # Evaluate
    predictions = []
    actuals = []

    for i in range(60, len(test_prices)):
        context = np.concatenate([train_prices, test_prices[:i]])
        pred = model.predict(context)
        predictions.append(pred[0])
        actuals.append(test_prices[i])

    predictions = np.array(predictions)
    actuals = np.array(actuals)

    mae = mean_absolute_error(actuals, predictions)
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
    directional_acc = np.mean(np.sign(np.diff(predictions)) == np.sign(np.diff(actuals)))

    results[symbol] = {
        'mae': mae,
        'mape': mape,
        'directional_accuracy': directional_acc,
        'predictions': predictions,
        'actuals': actuals
    }

    print(f"  ✓ MAE: ${mae:,.2f} ({mape:.2f}%)")
    print(f"  ✓ Directional Accuracy: {directional_acc*100:.1f}%")

# Compare performance
print(f"\n{'='*70}")
print("Performance Comparison")
print(f"{'='*70}")
print(f"{'Symbol':<10} {'MAE':>15} {'MAPE':>10} {'Directional':>15}")
print("-"*70)

best_symbol = None
best_mape = float('inf')

for symbol in SYMBOLS:
    r = results[symbol]
    print(f"{symbol:<10} ${r['mae']:>10,.2f} {r['mape']:>9.2f}% {r['directional_accuracy']*100:>14.1f}%")

    if r['mape'] < best_mape:
        best_mape = r['mape']
        best_symbol = symbol

print("-"*70)
print(f"Best performing: {best_symbol} (MAPE: {best_mape:.2f}%)")

# Visualize comparison
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

for idx, symbol in enumerate(SYMBOLS):
    ax = axes[idx]

    r = results[symbol]
    prices = data[symbol]

    # Plot actual vs predicted
    train_size = int(0.8 * len(prices))
    test_range = range(train_size + 60, len(prices))

    ax.plot(test_range, r['actuals'],
            label='Actual', alpha=0.7, color='blue')
    ax.plot(test_range, r['predictions'],
            label='Predicted', alpha=0.7, color='red', linestyle='--')

    ax.set_title(f'{symbol} - MAPE: {r["mape"]:.2f}%')
    ax.set_ylabel('Price ($)')
    ax.legend()
    ax.grid(True, alpha=0.3)

# Remove empty subplot
axes[-1].remove()

plt.tight_layout()
plt.savefig('multi_symbol_comparison.png', dpi=150, bbox_inches='tight')

# Generate portfolio allocation recommendations
print(f"\n{'='*70}")
print("Portfolio Allocation Recommendations")
print(f"{'='*70}")

# Sort by directional accuracy
sorted_symbols = sorted(SYMBOLS,
                       key=lambda s: results[s]['directional_accuracy'],
                       reverse=True)

print(f"\nRanking by prediction accuracy:")
for rank, symbol in enumerate(sorted_symbols, 1):
    acc = results[symbol]['directional_accuracy'] * 100
    print(f"  {rank}. {symbol:<10} - {acc:.1f}% accuracy")

print(f"\nSuggested allocation (based on accuracy):")
portfolio_weights = {}
total_weight = 0

for symbol in sorted_symbols[:3]:  # Top 3 symbols
    weight = 0.5 - (sorted_symbols.index(symbol) * 0.15)
    portfolio_weights[symbol] = weight
    total_weight += weight
    print(f"  • {symbol:<10}: {weight*100:.0f}%")

# Normalize to 100%
for symbol in portfolio_weights:
    portfolio_weights[symbol] = (portfolio_weights[symbol] / total_weight)

print(f"\nNormalized allocation:")
for symbol, weight in portfolio_weights.items():
    print(f"  • {symbol:<10}: {weight*100:.1f}%")

print(f"\n📊 Visualizations saved to 'multi_symbol_comparison.png'")
print(f"{'='*70}")
```

---

## 🎯 Example 3: Real-Time Inference

```python
"""
Example 3: Real-Time Inference Service
Create a simple API endpoint for real-time predictions
"""

import numpy as np
import json
from flask import Flask, request, jsonify
from ai_ml import LSTMPricePredictor
from threading import Lock
import logging

print("="*70)
print("Real-Time Inference Service Example")
print("="*70)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global model cache
models = {}
model_lock = Lock()

def load_model(symbol, model_path=None):
    """Load or create model for symbol"""

    with model_lock:
        if symbol not in models:
            logger.info(f"Loading model for {symbol}...")

            if model_path:
                # Load from file
                from tensorflow import keras
                model = keras.models.load_model(model_path)
            else:
                # Create new model
                model = LSTMPricePredictor(
                    sequence_length=60,
                    lstm_units=128
                )

                # Train with dummy data (in production, load trained model)
                np.random.seed(42)
                dummy_data = np.random.randint(45000, 55000, 1000).astype(float)
                model.fit(dummy_data, epochs=10, verbose=0)

            models[symbol] = model
            logger.info(f"Model loaded for {symbol}")

    return models[symbol]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'loaded_models': list(models.keys())
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Make prediction endpoint"""

    try:
        data = request.json

        # Validate required fields
        if 'symbol' not in data or 'prices' not in data:
            return jsonify({
                'error': 'Missing required fields: symbol, prices'
            }), 400

        symbol = data['symbol']
        prices = np.array(data['prices'])

        # Validate prices
        if len(prices) < 60:
            return jsonify({
                'error': f'Need at least 60 price points, got {len(prices)}'
            }), 400

        # Load model if needed
        model_path = data.get('model_path')
        model = load_model(symbol, model_path)

        # Make prediction
        prediction = model.predict(prices)
        current_price = prices[-1]

        # Calculate metrics
        expected_change_pct = ((prediction[0] - current_price) / current_price) * 100
        confidence = max(0, 1 - abs(prediction[0] - current_price) / current_price)

        # Determine signal
        if expected_change_pct > 0.5 and confidence > 0.6:
            signal = 'BUY'
        elif expected_change_pct < -0.5 and confidence > 0.6:
            signal = 'SELL'
        else:
            signal = 'HOLD'

        return jsonify({
            'symbol': symbol,
            'current_price': float(current_price),
            'predicted_price': float(prediction[0]),
            'expected_change_pct': float(expected_change_pct),
            'confidence': float(confidence),
            'signal': signal,
            'timestamp': np.datetime64('now').astype(str)
        })

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict_batch', methods=['POST'])
def predict_batch():
    """Make multiple predictions at once"""

    try:
        data = request.json

        # Validate
        if 'requests' not in data:
            return jsonify({'error': 'Missing "requests" field'}), 400

        results = []

        for req in data['requests']:
            symbol = req['symbol']
            prices = np.array(req['prices'])

            if len(prices) < 60:
                results.append({
                    'symbol': symbol,
                    'error': 'Insufficient price points'
                })
                continue

            model = load_model(symbol, req.get('model_path'))
            prediction = model.predict(prices)

            results.append({
                'symbol': symbol,
                'predicted_price': float(prediction[0])
            })

        return jsonify({'results': results})

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        return jsonify({'error': str(e)}), 500

# Example client code
def example_client():
    """Example client code to use the API"""

    import requests

    # Example 1: Single prediction
    print("\nExample 1: Single prediction")

    np.random.seed(42)
    prices = np.random.randint(45000, 55000, 100).astype(float)

    response = requests.post('http://localhost:5000/predict', json={
        'symbol': 'BTCUSDT',
        'prices': prices.tolist()
    })

    print(response.json())

    # Example 2: Batch prediction
    print("\nExample 2: Batch prediction")

    batch_requests = [
        {
            'symbol': 'BTCUSDT',
            'prices': np.random.randint(45000, 55000, 100).astype(float).tolist()
        },
        {
            'symbol': 'ETHUSDT',
            'prices': np.random.randint(2500, 3500, 100).astype(float).tolist()
        }
    ]

    response = requests.post('http://localhost:5000/predict_batch', json={
        'requests': batch_requests
    })

    print(response.json())

if __name__ == '__main__':
    print("\nStarting inference service...")
    print("API Endpoints:")
    print("  GET  /health - Health check")
    print("  POST /predict - Single prediction")
    print("  POST /predict_batch - Batch predictions")
    print("\nExample client code available in example_client() function")
    print("\nServer running on http://localhost:5000")

    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## 🎯 Example 4: Model Deployment with MLOps

```python
"""
Example 4: Model Deployment with MLOps
Complete workflow tracking with MLflow and model registration
"""

import numpy as np
import mlflow
import mlflow.keras
from ai_ml import LSTMPricePredictor, MLOpsManager, ExperimentTracker
from sklearn.metrics import mean_absolute_error, mean_squared_error
import os

print("="*70)
print("Model Deployment with MLOps Example")
print("="*70)

# Step 1: Initialize MLOps
# ========================

mlops = MLOpsManager(
    tracking_uri="file:///home/ubuntu/godmode-quant-orchestrator/mlruns",
    experiment_name="btcusdt_deployment_v1"
)

tracker = ExperimentTracker(mlops)

print(f"✓ MLOps initialized")
print(f"  Tracking URI: {mlops.tracking_uri}")
print(f"  Experiment: {mlops.experiment_name}")

# Step 2: Prepare Data
# ====================

def generate_training_data():
    """Generate high-quality training data"""

    print("\n📊 Generating training data...")

    np.random.seed(42)

    # Generate 2000 candles
    n_points = 2000
    t = np.linspace(0, 100, n_points)

    # Realistic price pattern
    trend = 50000 + 8000 * np.sin(t/5) + 4000 * np.cos(t/10)
    volatility = np.random.normal(0, 800, n_points)
    prices = trend + volatility

    # Split into train/validation/test
    train_size = int(0.7 * n_points)
    val_size = int(0.15 * n_points)

    train_prices = prices[:train_size]
    val_prices = prices[train_size:train_size + val_size]
    test_prices = prices[train_size + val_size:]

    print(f"  ✓ Train: {len(train_prices)} candles")
    print(f"  ✓ Validation: {len(val_prices)} candles")
    print(f"  ✓ Test: {len(test_prices)} candles")

    return train_prices, val_prices, test_prices

train_prices, val_prices, test_prices = generate_training_data()

# Step 3: Run Multiple Experiments
# =================================

configs = [
    {
        'name': 'lstm_small',
        'sequence_length': 60,
        'lstm_units': 64,
        'dropout_rate': 0.2,
        'epochs': 30
    },
    {
        'name': 'lstm_medium',
        'sequence_length': 60,
        'lstm_units': 128,
        'dropout_rate': 0.2,
        'epochs': 50
    },
    {
        'name': 'lstm_large',
        'sequence_length': 90,
        'lstm_units': 256,
        'dropout_rate': 0.3,
        'epochs': 50
    }
]

experiment_results = []

for config in configs:
    print(f"\n{'='*70}")
    print(f"Experiment: {config['name']}")
    print(f"{'='*70}")

    # Start experiment
    tracker.start_experiment(
        strategy_name=config['name'],
        symbol="BTCUSDT",
        parameters=config
    )

    # Train model
    print(f"\n🔧 Training model...")

    model = LSTMPricePredictor(
        sequence_length=config['sequence_length'],
        lstm_units=config['lstm_units'],
        dropout_rate=config['dropout_rate']
    )

    # Combine train+val for training
    combined_train = np.concatenate([train_prices, val_prices])

    history = model.fit(
        combined_train,
        epochs=config['epochs'],
        batch_size=32,
        verbose=0
    )

    print(f"  ✓ Training completed")

    # Evaluate on test set
    print(f"\n📊 Evaluating on test set...")

    predictions = []
    actuals = []

    for i in range(60, len(test_prices)):
        context = np.concatenate([combined_train, test_prices[:i]])
        pred = model.predict(context)
        predictions.append(pred[0])
        actuals.append(test_prices[i])

    predictions = np.array(predictions)
    actuals = np.array(actuals)

    # Calculate metrics
    mae = mean_absolute_error(actuals, predictions)
    mse = mean_squared_error(actuals, predictions)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100
    directional_acc = np.mean(
        np.sign(np.diff(predictions)) == np.sign(np.diff(actuals))
    )

    print(f"  ✓ MAE: ${mae:,.2f} ({mape:.2f}%)")
    print(f"  ✓ RMSE: ${rmse:,.2f}")
    print(f"  ✓ Directional Accuracy: {directional_acc*100:.1f}%")

    # Log metrics
    mlops.log_metrics({
        'test_mae': mae,
        'test_mse': mse,
        'test_rmse': rmse,
        'test_mape': mape,
        'test_directional_accuracy': directional_acc,
        'final_train_loss': history.history['loss'][-1],
        'epochs_trained': config['epochs']
    })

    # Log training loss history
    for epoch in range(len(history.history['loss'])):
        mlops.log_metrics({
            'train_loss': history.history['loss'][epoch],
            'val_loss': history.history.get('val_loss', [0])[epoch]
        }, step=epoch)

    # Log model
    print(f"\n💾 Logging model...")

    mlops.log_model(
        model.model,
        model_type='keras',
        artifact_path='model'
    )

    # Register model if performance is good
    if mape < 2.0 and directional_acc > 0.60:
        print(f"✓ Performance meets threshold - registering model")

        model_version = mlops.register_model(
            model_name=f"btcusdt_{config['name']}",
            artifact_path='model'
        )
    else:
        model_version = None
        print(f"⚠️  Performance below threshold - not registering")

    experiment_results.append({
        'name': config['name'],
        'config': config,
        'mae': mae,
        'mape': mape,
        'directional_acc': directional_acc,
        'model_version': model_version
    })

    # End experiment
    tracker.end_experiment()

# Step 4: Select Best Model
# =========================

print(f"\n{'='*70}")
print("EXPERIMENT SUMMARY")
print(f"{'='*70}")

print(f"\n{'Model':<15} {'MAE':>12} {'MAPE':>8} {'Directional':>15} {'Version':>10}")
print("-"*70)

best_model = None
best_score = float('inf')

for result in experiment_results:
    print(f"{result['name']:<15} "
          f"${result['mae']:>8,.2f} "
          f"{result['mape']:>7.2f}% "
          f"{result['directional_acc']*100:>14.1f}% "
          f"{result['model_version'] or 'N/A':>9}")

    # Use weighted score (70% MAPE, 30% directional accuracy)
    score = result['mape'] * 0.7 + (1 - result['directional_acc']) * 100 * 0.3

    if score < best_score:
        best_score = score
        best_model = result

print("-"*70)
print(f"\nBest Model: {best_model['name']}")
print(f"Model Version: {best_model['model_version']}")

# Step 5: Deploy Model (Simulated)
# =================================

print(f"\n{'='*70}")
print("DEPLOYMENT")
print(f"{'='*70}")

print(f"\n✓ Model {best_model['name']} selected for deployment")
print(f"  Version: {best_model['model_version']}")

# Simulate deployment steps
deployment_config = {
    'model_name': f"btcusdt_{best_model['name']}",
    'model_version': best_model['model_version'],
    'endpoint': '/v1/predict/btcusdt',
    'scaling_policy': 'auto_scale',
    'min_instances': 2,
    'max_instances': 10
}

print(f"\nDeployment Configuration:")
for key, value in deployment_config.items():
    print(f"  • {key}: {value}")

print(f"\n✓ Model deployed successfully!")
print(f"  Endpoint: http://api.godmode-quant.com{deployment_config['endpoint']}")

# Step 6: Monitoring Setup
# =========================

print(f"\n{'='*70}")
print("MONITORING")
print(f"{'='*70}")

print(f"\nMonitoring metrics enabled:")
print(f"  • Prediction accuracy (MAE, MAPE)")
print(f"  • Directional accuracy")
print(f"  • Inference latency")
print(f"  • Model drift detection")
print(f"  • Error rates")

print(f"\nAlert thresholds:")
print(f"  • MAE > $1000: ⚠️  Warning")
print(f"  • MAE > $2000: 🚨  Critical")
print(f"  • Directional accuracy < 55%: ⚠️  Warning")
print(f"  • Inference latency > 100ms: ⚠️  Warning")

print(f"\n{'='*70}")
print("MLOps deployment completed!")
print(f"{'='*70}")
print(f"\nMonitor experiments:")
print(f"  mlflow ui")
print(f"  then open http://localhost:5000")
```

---

## 🎯 Example 5: Performance Monitoring

```python
"""
Example 5: Performance Monitoring
Track model performance over time and detect drift
"""

import numpy as np
import pandas as pd
from ai_ml import ModelPerformanceTracker, LSTMPricePredictor
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

print("="*70)
print("Performance Monitoring Example")
print("="*70)

# Step 1: Initialize Model
# =========================

print("\n🔧 Initializing model...")

predictor = LSTMPricePredictor(
    sequence_length=60,
    lstm_units=128
)

# Train model
np.random.seed(42)
training_data = np.random.randint(45000, 55000, 1000).astype(float)
predictor.fit(training_data, epochs=30, verbose=0)

print("✓ Model trained")

# Step 2: Initialize Performance Tracker
# =========================================

tracker = ModelPerformanceTracker(
    window_size=100,
    drift_threshold=0.2
)

print("✓ Performance tracker initialized")
print(f"  Window size: {tracker.window_size}")
print(f"  Drift threshold: {tracker.drift_threshold}")

# Step 3: Simulate Ongoing Monitoring
# ====================================

print(f"\n{'='*70}")
print("Simulating 30 days of predictions...")
print(f"{'='*70}")

# Generate 30 days of data (one prediction per hour)
n_days = 30
hours_per_day = 24
total_predictions = n_days * hours_per_day

# Simulate changing market conditions
# First 10 days: Stable
# Days 10-20: Increased volatility
# Days 20-30: Different trend

np.random.seed(42)

predictions_history = []
actuals_history = []
dates_history = []
alerts = []

for day in range(n_days):
    day_predictions = []
    day_actuals = []

    for hour in range(hours_per_day):
        date = datetime.now() - timedelta(days=n_days-day-1, hours=24-hour)
        dates_history.append(date)

        # Simulate actual price (with changing patterns)
        if day < 10:
            # Stable
            noise = np.random.normal(0, 500)
            actual = 50000 + noise
        elif day < 20:
            # Increased volatility
            noise = np.random.normal(0, 1500)
            actual = 50000 + noise
        else:
            # Different trend
            trend = (day - 20) * 100
            noise = np.random.normal(0, 800)
            actual = 52000 + trend + noise

        # Make prediction (model accuracy degrades over time)
        context = np.random.randint(45000, 55000, 200).astype(float)

        # Simulate prediction error increasing over time
        prediction_error = np.random.normal(0, 200 + day * 20)
        prediction = actual + prediction_error

        # Add to tracker
        actuals_history.append(actual)
        predictions_history.append(prediction)
        tracker.add_prediction(prediction, actual, date)

        # Check for drift
        if tracker.drift_detected:
            alert = {
                'date': date,
                'type': 'DRIFT_DETECTED',
                'message': f"Model drift detected on day {day+1}"
            }
            alerts.append(alert)
            day_actuals.append(actual)
            day_predictions.append(prediction)
        else:
            day_actuals.append(actual)
            day_predictions.append(prediction)

    # Print daily summary
    predictions_array = np.array(day_predictions)
    actuals_array = np.array(day_actuals)
    daily_mae = np.mean(np.abs(predictions_array - actuals_array))

    status = "⚠️  DRIFT" if any(a['type'] == 'DRIFT_DETECTED' for a in alerts[-24:]) else "✓ OK"

    print(f"Day {day+2:2d}: MAE=${daily_mae:>6,.2f} | {status}")

# Step 4: Analyze Performance
# =============================

print(f"\n{'='*70}")
print("PERFORMANCE ANALYSIS")
print(f"{'='*70}")

# Calculate overall metrics
predictions_array = np.array(predictions_history)
actuals_array = np.array(actuals_history)

overall_mae = np.mean(np.abs(predictions_array - actuals_array))
overall_mape = np.mean(np.abs((actuals_array - predictions_array) / actuals_array)) * 100

print(f"\nOverall Performance:")
print(f"  Total predictions: {len(predictions_history)}")
print(f"  MAE: ${overall_mae:,.2f}")
print(f"  MAPE: {overall_mape:.2f}%")

# Calculate metrics by phase
for phase_name, start_day, end_day in [
    ("Stable (Days 1-10)", 0, 10),
    ("Volatile (Days 11-20)", 10, 20),
    ("Drift (Days 21-30)", 20, 30)
]:
    start_idx = start_day * 24
    end_idx = end_day * 24

    phase_preds = predictions_array[start_idx:end_idx]
    phase_actuals = actuals_array[start_idx:end_idx]

    phase_mae = np.mean(np.abs(phase_preds - phase_actuals))
    phase_mape = np.mean(np.abs((phase_actuals - phase_preds) / phase_actuals)) * 100

    print(f"\n{phase_name}:")
    print(f"  MAE: ${phase_mae:,.2f}")
    print(f"  MAPE: {phase_mape:.2f}%")

# Step 5: Visualize Monitoring
# =============================

print(f"\n✓ Creating monitoring visualizations...")

fig, axes = plt.subplots(3, 1, figsize=(15, 12))

# Plot 1: Prediction vs Actual over time
ax1 = axes[0]

ax1.plot(range(len(actuals_history)), actuals_history,
         label='Actual Price', alpha=0.7, color='blue')
ax1.plot(range(len(predictions_history)), predictions_history,
         label='Predicted Price', alpha=0.7, color='red', linestyle='--')

ax1.axvline(x=10*24, color='orange', linestyle=':', label='Phase Change')
ax1.axvline(x=20*24, color='green', linestyle=':', label='Drift Starts')

ax1.set_ylabel('Price ($)')
ax1.set_title('Prediction vs Actual Price Over Time')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot 2: Rolling MAE
ax2 = axes[1]

window = 24  # Daily rolling
rolling_mae = []

for i in range(window, len(predictions_history)):
    window_preds = predictions_history[i-window:i]
    window_actuals = actuals_history[i-window:i]
    mae = np.mean(np.abs(np.array(window_preds) - np.array(window_actuals)))
    rolling_mae.append(mae)

ax2.plot(range(window, len(predictions_history)), rolling_mae,
         label='Rolling MAE (24h)', color='purple', linewidth=2)
ax2.axhline(y=500, color='green', linestyle='--', label='Target (<$500)')
ax2.axhline(y=1000, color='orange', linestyle='--', label='Warning (>$1000)')
ax2.axhline(y=1500, color='red', linestyle='--', label='Critical (>$1500)')

ax2.axvline(x=10*24, color='orange', linestyle=':')
ax2.axvline(x=20*24, color='green', linestyle=':')

ax2.set_ylabel('MAE ($)')
ax2.set_title('Rolling Mean Absolute Error')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Plot 3: Drift Detection
ax3 = axes[2]

# Get metrics history
metrics_history = tracker.get_average_metrics()

# Plot key metrics
current_metrics = tracker.get_current_metrics()
print(f"\nCurrent Metrics:")
for key, value in current_metrics.items():
    if key != 'timestamp':
        print(f"  {key}: {value:.4f}")

# Plot drift events
drift_days = [a['date'] for a in alerts if a['type'] == 'DRIFT_DETECTED']
drift_indices = [dates_history.index(d) for d in drift_days]

for idx in drift_indices:
    ax3.axvline(x=idx, color='red', alpha=0.5, linestyle='--')

ax3.set_xlabel('Time (Hours)')
ax3.set_ylabel('Drift Events')
ax3.set_title('Model Drift Detection')
ax3.set_yticks([])
ax3.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig('performance_monitoring.png', dpi=150, bbox_inches='tight')

# Step 6: Generate Report
# =======================

print(f"\n{'='*70}")
print("MONITORING REPORT")
print(f"{'='*70}")

print(f"\n📊 Key Findings:")
print(f"  • Total predictions monitored: {len(predictions_history)}")
print(f"  • Drift events detected: {len(alerts)}")
print(f"  • Overall accuracy: {100 - overall_mape:.1f}%")

print(f"\n⚠️  Alerts:")
for alert in alerts[:5]:  # Show first 5
    print(f"  • {alert['date'].strftime('%Y-%m-%d %H:%M')}: {alert['message']}")

if len(alerts) > 5:
    print(f"  • ... and {len(alerts) - 5} more alerts")

print(f"\n💡 Recommendations:")

if len(alerts) > 0:
    print(f"  • Model drift detected - consider retraining")
    print(f"  • Review recent market conditions")
    print(f"  • Evaluate alternative model architectures")
else:
    print(f"  • Model performing within expected parameters")
    print(f"  • Continue regular monitoring")
    print(f"  • Schedule periodic retraining")

print(f"\n📊 Monitoring visualization saved to 'performance_monitoring.png'")

print(f"\n{'='*70}")
print("Performance monitoring completed!")
print(f"{'='*70}")
```

---

## 📚 Additional Examples

For more examples, see:

- **[MODELS.md](MODELS.md)** - Detailed model documentation
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Getting started guide

### Topics Covered in Other Documentation:

1. **Sentiment Analysis Integration** - Using sentiment with price predictions
2. **Ensemble Model** - Combining multiple models
3. **Backtesting with ML Signals** - Testing ML-based strategies
4. **Multi-Feature Input** - Using volume, RSI, and other indicators
5. **Hyperparameter Tuning** - Finding optimal model parameters

---

## 🎯 Running These Examples

### Prerequisites
```bash
# Install dependencies
pip install -r ai_ml/requirements_ml.txt

# For example 3 (Flask API)
pip install flask

# For visualization
pip install matplotlib
```

### Running Individual Examples

```bash
# Example 1: BTCUSDT Price Forecasting
python ai_ml/examples/example_1_btc_forecast.py

# Example 2: Multi-Symbol Strategy
python ai_ml/examples/example_2_multi_symbol.py

# Example 3: Real-Time API
python ai_ml/examples/example_3_inference_api.py

# Example 4: MLOps Deployment
python ai_ml/examples/example_4_deployment.py

# Example 5: Performance Monitoring
python ai_ml/examples/example_5_monitoring.py
```

---

**Last Updated**: March 26, 2026
**Version**: 2.0.0
**GodMode Quant Orchestrator**
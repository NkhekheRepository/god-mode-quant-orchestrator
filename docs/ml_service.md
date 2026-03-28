# ML Service Layer Documentation

## Overview

The ML Service Layer provides a unified interface for integrating machine learning models with the GodMode Quant Trading Orchestrator. It enables enhanced trading signals through deep learning forecasting (LSTM, Transformer) and includes MLOps capabilities for model lifecycle management.

Key features:
- Deep learning models: LSTM, Transformer, Hybrid Ensemble
- MLOps integration with MLflow for experiment tracking and model registry
- Signal generation capabilities for trading decisions
- Graceful fallback when ML dependencies are unavailable
- Performance monitoring and automatic retraining

## Architecture

The ML service consists of:
1. **Model Initialization**: Loads configured ML models (LSTM, Transformer, etc.)
2. **Prediction Engine**: Generates trading signals from historical data
3. **Training Manager**: Handles model training and retraining schedules
4. **MLflow Integration**: Tracks experiments and manages model versions
5. **Performance Monitoring**: Tracks prediction accuracy and service health

![ML Service Architecture](assets/ml-service-architecture.png)

## Configuration

The ML service is configured through environment variables passed to the trading engine or set in the `.env` file.

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `USE_ML_PREDICTIONS` | Enable/disable ML predictions | `true` | No |
| `ML_MODEL_PATH` | Directory for storing models | `./ml_models` | No |
| `RETRAIN_SCHEDULE` | Retraining frequency (`hourly`, `daily`, `weekly`) | `daily` | No |
| `ML_CONFIDENCE_THRESHOLD` | Minimum confidence for signals | `0.6` | No |
| `ML_MODEL_TYPE` | Model type (`lstm`, `transformer`, `hybrid`, `timeseries`, `ensemble`) | `ensemble` | No |
| `MLFLOW_TRACKING_URI` | MLflow tracking server URI | `file://./mlruns` | No |
| `MLFLOW_EXPERIMENT_NAME` | MLflow experiment name | `godmode-quant-trading-ml` | No |
| `LSTM_SEQUENCE_LENGTH` | LSTM lookback window | `60` | No |
| `LSTM_UNITS` | LSTM units | `128` | No |
| `TRANSFORMER_SEQUENCE_LENGTH` | Transformer lookback window | `60` | No |
| `TRANSFORMER_HEADS` | Number of attention heads | `4` | No |
| `TRANSFORMER_EMBED_DIM` | Embedding dimension | `128` | No |
| `TRANSFORMER_FF_DIM` | Feed-forward dimension | `256` | No |
| `TRANSFORMER_LAYERS` | Number of transformer layers | `3` | No |
| `TRANSFORMER_DROPOUT` | Dropout rate | `0.1` | No |
| `TRANSFORMER_LR` | Learning rate | `0.0001` | No |

### Example Configuration (.env)

```bash
# Enable ML predictions
USE_ML_PREDICTIONS=true

# Model configuration
ML_MODEL_TYPE=ensemble
ML_CONFIDENCE_THRESHOLD=0.7
RETRAIN_SCHEDULE=daily

# MLflow tracking
MLFLOW_TRACKING_URI=file:///home/ubuntu/godmode-quant-orchestrator/mlruns
MLFLOW_EXPERIMENT_NAME=godmode-quant-trading-ml

# LSTM parameters
LSTM_SEQUENCE_LENGTH=60
LSTM_UNITS=128

# Transformer parameters
TRANSFORMER_SEQUENCE_LENGTH=60
TRANSFORMER_HEADS=4
TRANSFORMER_EMBED_DIM=128
TRANSFORMER_FF_DIM=256
TRANSFORMER_LAYERS=3
TRANSFORMER_DROPOUT=0.1
TRANSFORMER_LR=0.0001
```

## Usage

### Initialization

The ML service is automatically initialized when the trading engine starts if `ML_SERVICE_AVAILABLE` is true and `ml_enabled` is set in the configuration.

```python
# In trading_engine.py
self.ml_enabled = self.config.get('ml_enabled', True) and ML_SERVICE_AVAILABLE

# During initialization
if self.ml_enabled:
    try:
        self._init_ml_service()
        initialized_components.append("ml_service")
    except Exception as e:
        logger.warning(f"ML Service initialization failed: {e}")
```

### Getting ML Predictions

The trading engine collects ML predictions during each trading cycle to enhance strategy signals.

```python
# In trading_engine.py _collect_signals method
# ML predictions can be incorporated here to boost signal confidence

def _get_ml_enhanced_confidence(self, base_confidence: float) -> float:
    """Enhance strategy confidence with ML prediction"""
    if not self.ml_service or not self.ml_service.is_initialized:
        return base_confidence
    
    # Get ML prediction using recent price/volume history
    if len(self.ml_price_history) < 50:  # Need minimum data
        return base_confidence
        
    price_data = np.array(self.ml_price_history[-50:])
    volume_data = np.array(self.ml_volume_history[-50:]) if self.ml_volume_history else None
    
    ml_prediction = self.ml_service.get_ml_prediction(price_data, volume_data)
    
    # Combine strategy confidence with ML confidence
    if ml_prediction['signal'] != 0 and ml_prediction['confidence'] > self.ml_confidence_threshold:
        # ML agrees with signal direction - boost confidence
        if (ml_prediction['signal'] > 0 and base_confidence > 0) or \
           (ml_prediction['signal'] < 0 and base_confidence < 0):
            return min(base_confidence + (ml_prediction['confidence'] * 0.3), 1.0)
        else:
            # ML disagrees - reduce confidence
            return base_confidence * 0.7
    
    return base_confidence
```

### Direct ML Service Usage

You can also use the ML service directly for custom applications:

```python
from ml_service import get_ml_service, initialize_ml_service
import numpy as np

# Initialize ML service (if not already done by trading engine)
ml_config = {
    'ml_enabled': True,
    'use_ml_predictions': True,
    'ml_model_type': 'ensemble',
    'ml_confidence_threshold': 0.6
}
ml_service = initialize_ml_service(ml_config)

# Prepare historical data
prices = np.array([50000, 50100, 49900, 50200, ...])  # Array of historical prices
volume = np.array([100, 150, 120, 180, ...])          # Optional volume data

# Get ML prediction
prediction = ml_service.get_ml_prediction(prices, volume)

print(f"Signal: {prediction['signal']}")  # -1 (sell), 0 (hold), 1 (buy)
print(f"Confidence: {prediction['confidence']:.2f}")
print(f"Predicted Price: ${prediction['predicted_price']:.2f}")
print(f"Expected Change: {prediction['expected_change']*100:.2f}%")
```

## Model Types

### LSTM (Long Short-Term Memory)
- **Best for**: Capturing temporal dependencies in sequential data
- **Configuration**: 
  - `sequence_length`: Lookback window (default: 60)
  - `lstm_units`: Number of LSTM units (default: 128)
  - `bidirectional`: Use bidirectional LSTM (default: True via underlying implementation)
- **Output**: Price prediction and trading signal (-1, 0, 1)

### Transformer
- **Best for**: Capturing long-range dependencies with self-attention
- **Configuration**:
  - `sequence_length`: Lookback window (default: 60)
  - `num_heads`: Number of attention heads (default: 4)
  - `embed_dim`: Embedding dimension (default: 128)
  - `ff_dim`: Feed-forward dimension (default: 256)
  - `num_layers`: Number of transformer blocks (default: 3)
- **Output**: Price prediction and trading signal (-1, 0, 1)

### Hybrid Ensemble
- **Best for**: Combining strengths of LSTM and Transformer for improved robustness
- **Configuration**: Inherits parameters from both LSTM and Transformer
- **Output**: Weighted average prediction from both models

### Time Series (Traditional)
- **Best for**: Fallback when deep learning libraries are unavailable
- **Models**: Random Forest, Linear Regression (via `time_series_forecast.py`)
- **Output**: Price prediction and trading signal

## MLOps Integration

The ML service integrates with MLflow for experiment tracking and model management.

### Experiment Tracking

All model training runs are automatically logged to MLflow when available:
- Hyperparameters (learning rate, sequence length, etc.)
- Metrics (MAE, MSE, RMSE)
- Model artifacts
- Training duration

### Model Registry

Trained models are registered in the MLflow Model Registry:
- Models are versioned automatically
- Can promote models to "Staging" or "Production" stages
- Enables A/B testing and rollback capabilities

### Accessing MLflow UI

Start the MLflow UI to view experiments and models:
```bash
mlflow ui --backend-store-uri ./mlruns
```
Then visit `http://localhost:5000` in your browser.

## Performance Monitoring

The ML service tracks key performance metrics:

### Internal Metrics
- `total_predictions`: Number of predictions made
- `successful_predictions`: Predictions with confidence > 0
- `avg_confidence`: Average confidence across all predictions
- `last_prediction_time`: Timestamp of last prediction

### Accessing Metrics

```python
# Get performance metrics from ML service
metrics = ml_service.get_performance_metrics()
print(f"Total Predictions: {metrics['total_predictions']}")
print(f"Average Confidence: {metrics['avg_confidence']:.2f}")
print(f"Models Available: {metrics['models_available']}")
```

### Health Check Endpoint

The trading engine provides a health endpoint that includes ML service status:
```bash
curl -u admin:password http://localhost:8000/health
```
Response includes:
```json
{
  "ml_service": {
    "status": "initialized",
    "ml_enabled": true,
    "model_type": "ensemble",
    "models_loaded": ["lstm", "transformer", "hybrid", "timeseries"],
    "performance": {
      "total_predictions": 1420,
      "successful_predictions": 1280,
      "avg_confidence": 0.78,
      "last_prediction_time": "2026-03-27T05:00:00"
    }
  }
}
```

## Integration with Trading Engine

The ML service enhances the trading engine in several ways:

### 1. Signal Confidence Enhancement
As shown in the usage example above, ML predictions can boost or reduce strategy signal confidence based on agreement.

### 2. Regime Detection
The ML service can help identify market regimes (trending, ranging, volatile) which informs strategy selection.

### 3. Risk Management Adjustments
ML predictions of volatility or potential drawdowns can inform dynamic position sizing.

### 4. Early Warning System
Unusual ML prediction patterns can trigger alerts for potential market regime changes.

## Best Practices

### 1. Data Requirements
- Minimum 50 data points for reliable predictions
- More data (100-200 points) improves accuracy
- Ensure data is clean and free of major gaps

### 2. Model Selection
- Start with `ensemble` for best performance
- Use `lstm` for faster inference when Transformer is too slow
- Use `timeseries` as fallback in resource-constrained environments

### 3. Confidence Threshold
- Default threshold of 0.6 works for most cases
- Increase to 0.7-0.8 for more conservative signals
- Decrease to 0.5 for more aggressive trading (more signals)

### 4. Retraining Schedule
- `hourly`: For highly volatile markets or intraday strategies
- `daily`: Recommended for most swing trading strategies
- `weekly`: For longer-term position trading

### 5. Monitoring
- Monitor prediction confidence trends
- Watch for degradation in performance metrics
- Set up alerts for when confidence consistently falls below threshold

## Troubleshooting

### Common Issues

#### 1. "TensorFlow not available" Error
```bash
# Solution: Install TensorFlow
pip install tensorflow
# Or set USE_BASIC_MODELS=true to use traditional models
```

#### 2. Poor Prediction Accuracy
- Check that you're using sufficient historical data (min 50 points)
- Verify that your data is normalized appropriately
- Consider increasing model complexity (more LSTM units, transformer layers)
- Check for data leakage or look-ahead bias

#### 3. ML Service Not Initializing
- Verify `USE_ML_PREDICTIONS=true` in environment
- Check that required ML packages are installed (tensorflow, transformers, etc.)
- Look at logs for specific initialization errors
- Ensure write permissions to `ML_MODEL_PATH`

#### 4. Slow Inference
- Consider reducing sequence length
- Use smaller models (fewer LSTM units/transformer layers)
- Enable model caching (already implemented in service)
- Consider using CPU-optimized TensorFlow builds

## Security Considerations

1. **Model Security**: ML models are stored locally and should be protected like any other asset
2. **Data Privacy**: Training data should not contain sensitive information
3. **API Security**: When using MLflow tracking server, ensure proper authentication is configured
4. **Dependency Security**: Regularly update ML dependencies (tensorflow, torch, etc.) to patch vulnerabilities

## Further Reading

- [AI/ML Modernization Report](../AI_ML_MODERNIZATION.md): Details the ML upgrade journey
- [MLOps Documentation](ai_ml/mlops.py): Inline documentation of MLflow integration
- [LSTM Forecasting](ai_ml/lstm_forecast.py): LSTM model implementation
- [Transformer Forecasting](ai_ml/transformer_forecast.py): Transformer and hybrid model implementation
- [Time Series Forecasting](ai_ml/time_series_forecast.py): Traditional forecasting models

---
*Last Updated: March 27, 2026*
*ML Service Version: 1.0.0*
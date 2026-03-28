"""
AI/ML Module for GodMode Quant Trading Orchestrator v2.0.0

This module provides comprehensive machine learning capabilities for cryptocurrency
trading, including price forecasting, signal generation, and MLOps infrastructure.

Available Models:
    - LSTMPricePredictor: Deep learning model for short-to-medium term forecasting
    - TransformerPricePredictor: Attention-based model for long-term dependencies
    - HybridPredictor: Ensemble combining LSTM and Transformer strengths
    - LSTMSignalGenerator: Trading signal generation with confidence scoring
    - TimeSeriesForecaster: Traditional ML models for quick predictions

MLOps Infrastructure:
    - MLOpsManager: Central MLOps manager for experiment tracking
    - ModelPerformanceTracker: Performance monitoring and drift detection
    - ExperimentTracker: Trading experiment tracking with MLflow integration

Example Usage:
    >>> from ai_ml import LSTMPricePredictor
    >>> predictor = LSTMPricePredictor(sequence_length=60, lstm_units=128)
    >>> predictor.fit(prices, epochs=50)
    >>> prediction = predictor.predict(prices)

For more information, see:
    - MODELS.md: Complete model documentation and benchmarks
    - GETTING_STARTED.md: Quick start guide and installation
    - EXAMPLES.md: Practical usage examples
"""

__version__ = '2.0.0'
__author__ = 'GodMode Quant Team'

# Check for PyTorch availability (preferred - compatible with numpy>=2.2.3)
try:
    import torch
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

# Check for TensorFlow availability (fallback)
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

# Check for MLflow availability
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

# Import LSTM models (try PyTorch first, then TensorFlow fallback)
try:
    from .lstm_forecast_pytorch import (
        LSTMPricePredictor,
        LSTMSignalGenerator
    )
    LSTM_MODELS_AVAILABLE = True
except ImportError:
    try:
        from .lstm_forecast import (
            LSTMPricePredictor,
            LSTMSignalGenerator
        )
        LSTM_MODELS_AVAILABLE = True
    except ImportError:
        LSTM_MODELS_AVAILABLE = False

# Import Transformer models (try PyTorch first, then TensorFlow fallback)
try:
    from .transformer_forecast_pytorch import (
        TransformerPricePredictor,
        HybridPredictor
    )
    TRANSFORMER_MODELS_AVAILABLE = True
except ImportError:
    try:
        from .transformer_forecast import (
            TransformerPricePredictor,
            HybridPredictor
        )
        TRANSFORMER_MODELS_AVAILABLE = True
    except ImportError:
        TRANSFORMER_MODELS_AVAILABLE = False

# Import MLOps infrastructure
try:
    from .mlops import (
        MLOpsManager,
        ModelPerformanceTracker,
        ExperimentTracker,
        initialize_mlops
    )
    MLOPS_AVAILABLE = True
except ImportError:
    MLOPS_AVAILABLE = False

# Import Time Series Forecaster
try:
    from .time_series_forecast import (
        TimeSeriesForecaster,
        EnhancedMaCrossoverStrategy
    )
    TIME_SERIES_AVAILABLE = True
except ImportError:
    TIME_SERIES_AVAILABLE = False

# Import Sentiment Analyzer
try:
    from .sentiment_analysis import (
        SentimentAnalyzer,
        NewsSentimentFetcher,
        SocialMediaSentimentFetcher,
        EnhancedSentimentStrategy
    )
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

# Define what's publicly available
__all__ = [
    # Version info
    '__version__',
    '__author__',

    # Availability flags
    'PYTORCH_AVAILABLE',
    'TENSORFLOW_AVAILABLE',
    'MLFLOW_AVAILABLE',
    'LSTM_MODELS_AVAILABLE',
    'TRANSFORMER_MODELS_AVAILABLE',
    'MLOPS_AVAILABLE',
    'TIME_SERIES_AVAILABLE',
    'SENTIMENT_AVAILABLE',

    # LSTM Models
    'LSTMPricePredictor',
    'LSTMSignalGenerator',

    # Transformer Models
    'TransformerPricePredictor',
    'HybridPredictor',

    # Traditional ML Models
    'TimeSeriesForecaster',
    'EnhancedMaCrossoverStrategy',

    # Sentiment Analysis
    'SentimentAnalyzer',
    'NewsSentimentFetcher',
    'SocialMediaSentimentFetcher',
    'EnhancedSentimentStrategy',

    # MLOps
    'MLOpsManager',
    'ModelPerformanceTracker',
    'ExperimentTracker',
    'initialize_mlops',
]

# Module docstring for help()
__doc__ += """

Compatibility:
    All models work with or without GPU. CPU-only operation is fully supported,
    though training will be slower.

    TensorFlow is optional but required for deep learning models (LSTM, Transformer).
    If TensorFlow is not available, you can still use TimeSeriesForecaster and
    sentiment analysis features.

Quick Start:
    1. Install dependencies: pip install -r ai_ml/requirements_ml.txt
    2. Import model: from ai_ml import LSTMPricePredictor
    3. Train model: predictor = LSTMPricePredictor(); predictor.fit(data)
    4. Make predictions: prediction = predictor.predict(data)

Performance Tips:
    - Use GPU for faster training (if available)
    - Increase batch size for better GPU utilization
    - Use HybridPredictor for best accuracy
    - Use TimeSeriesForecaster for fastest inference

Production Deployment:
    - Use MLOpsManager for experiment tracking
    - Enable ModelPerformanceTracker for drift detection
    - Register models with MLflow for version control
    - Monitor inference latency and accuracy metrics

Troubleshooting:
    - If TensorFlow import fails: pip install tensorflow>=2.13.0
    - If MLflow import fails: pip install mlflow>=2.7.0
    - If GPU not detected: Install CUDA drivers and cuDNN
    - For memory errors: Reduce batch_size or model size

See MODELS.md for detailed documentation and performance benchmarks.
"""

# Print availability warnings on import
def _print_availability_info():
    """Print information about available components"""
    import sys

    if '--quiet' not in sys.argv and '-q' not in sys.argv:
        print(f"\n{'='*60}")
        print(f"AI/ML Module v{__version__} - GodMode Quant Orchestrator")
        print(f"{'='*60}")
        print(f"\nComponent Status:")

        components = [
            ('PyTorch', PYTORCH_AVAILABLE),
            ('TensorFlow', TENSORFLOW_AVAILABLE),
            ('MLflow', MLFLOW_AVAILABLE),
            ('LSTM Models', LSTM_MODELS_AVAILABLE),
            ('Transformer Models', TRANSFORMER_MODELS_AVAILABLE),
            ('MLOps Infrastructure', MLOPS_AVAILABLE),
            ('Time Series Forecaster', TIME_SERIES_AVAILABLE),
            ('Sentiment Analysis', SENTIMENT_AVAILABLE),
        ]

        for name, available in components:
            status = "✓ Available" if available else "✗ Not Available"
            print(f"  {name:<25} {status}")

        if not any([LSTM_MODELS_AVAILABLE, TRANSFORMER_MODELS_AVAILABLE]):
            print(f"\n⚠️  Deep learning models require TensorFlow")
            print(f"   Install with: pip install tensorflow>=2.13.0")

        if not MLFLOW_AVAILABLE:
            print(f"\n⚠️  MLOps features require MLflow")
            print(f"   Install with: pip install mlflow>=2.7.0")

        print(f"\nFor help: help(ai_ml)")
        print(f"Documentation: See MODELS.md, GETTING_STARTED.md, EXAMPLES.md")
        print(f"{'='*60}\n")

# Print availability info when module is imported directly (not as package)
if __name__ == '__main__':
    _print_availability_info()

def get_available_models():
    """
    Get list of available models based on installed dependencies

    Returns:
        dict: Dictionary with available models and their descriptions
    """
    models = {}

    if LSTM_MODELS_AVAILABLE:
        models['LSTMPricePredictor'] = {
            'class': LSTMPricePredictor,
            'description': 'Deep learning model for short-to-medium term forecasting',
            'use_case': 'Real-time trading, moderate volatility'
        }
        models['LSTMSignalGenerator'] = {
            'class': LSTMSignalGenerator,
            'description': 'Generate trading signals with confidence scoring',
            'use_case': 'Automated trading with risk filtering'
        }

    if TRANSFORMER_MODELS_AVAILABLE:
        models['TransformerPricePredictor'] = {
            'class': TransformerPricePredictor,
            'description': 'Attention-based model for long-term dependencies',
            'use_case': 'Long-term forecasting, volatile markets'
        }
        models['HybridPredictor'] = {
            'class': HybridPredictor,
            'description': 'Ensemble combining LSTM and Transformer',
            'use_case': 'Maximum accuracy, production systems'
        }

    if TIME_SERIES_AVAILABLE:
        models['TimeSeriesForecaster'] = {
            'class': TimeSeriesForecaster,
            'description': 'Traditional ML models for quick predictions',
            'use_case': 'Rapid prototyping, interpretability'
        }

    return models

def get_required_packages():
    """
    Get package requirements for different use cases

    Returns:
        dict: Dictionary mapping use cases to required packages
    """
    return {
        'minimal': ['numpy', 'pandas'],
        'basic_ml': ['numpy', 'pandas', 'scikit-learn'],
        'deep_learning': ['numpy', 'pandas', 'tensorflow'],
        'full': ['numpy', 'pandas', 'scikit-learn', 'tensorflow', 'mlflow'],
        'with_transformers': ['numpy', 'pandas', 'tensorflow', 'transformers'],
        'with_viz': ['numpy', 'pandas', 'matplotlib', 'seaborn'],
    }

def quick_start_example():
    """
    Quick start example demonstrating basic usage
    """
    print("\nQuick Start Example")
    print("="*60)

    if not LSTM_MODELS_AVAILABLE:
        print("⚠️  LSTM models not available. Install TensorFlow first.")
        return

    try:
        import numpy as np

        # Generate sample data
        np.random.seed(42)
        prices = np.random.randint(45000, 55000, 500).astype(float)
        print(f"✓ Generated {len(prices)} price points")

        # Create predictor
        predictor = LSTMPricePredictor(sequence_length=50, lstm_units=64)
        print("✓ Initialized LSTM predictor")

        # Train model
        print("✓ Training model...")
        predictor.fit(prices, epochs=10, verbose=0)

        # Make prediction
        prediction = predictor.predict(prices)
        current_price = prices[-1]

        print(f"✓ Prediction completed")
        print(f"\nResults:")
        print(f"  Current Price:  ${current_price:,.2f}")
        print(f"  Predicted Price: ${prediction[0]:,.2f}")
        print(f"  Expected Change: {((prediction[0] - current_price) / current_price) * 100:+.2f}%")

        print("\nFor more examples, see EXAMPLES.md")

    except Exception as e:
        print(f"⚠️  Example failed: {e}")

if __name__ == '__main__':
    # Run quick start example
    quick_start_example()
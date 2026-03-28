"""
ML Service Layer for GodMode Quant Trading Orchestrator
Provides unified interface for ML models integration with trading engine
"""

import os
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Import ML models with fallback handling
# Try PyTorch implementations first (compatible with numpy>=2.2.3)
try:
    from ai_ml.lstm_forecast_pytorch import LSTMSignalGenerator, LSTMPricePredictor
    LSTM_AVAILABLE = True
    logger.info("Using PyTorch LSTM implementation")
except ImportError as e:
    # Fallback to TensorFlow implementation if available
    try:
        from ai_ml.lstm_forecast import LSTMSignalGenerator, LSTMPricePredictor
        LSTM_AVAILABLE = True
        logger.info("Using TensorFlow LSTM implementation")
    except ImportError as e2:
        logger.warning(f"LSTM models not available: {e2}")
        LSTM_AVAILABLE = False

try:
    from ai_ml.transformer_forecast_pytorch import TransformerPricePredictor, HybridPredictor
    TRANSFORMER_AVAILABLE = True
    logger.info("Using PyTorch Transformer implementation")
except ImportError as e:
    # Fallback to TensorFlow implementation if available
    try:
        from ai_ml.transformer_forecast import TransformerPricePredictor, HybridPredictor
        TRANSFORMER_AVAILABLE = True
        logger.info("Using TensorFlow Transformer implementation")
    except ImportError as e2:
        logger.warning(f"Transformer models not available: {e2}")
        TRANSFORMER_AVAILABLE = False

try:
    from ai_ml.time_series_forecast import TimeSeriesForecaster, EnhancedMaCrossoverStrategy
    TIMESERIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Time series models not available: {e}")
    TIMESERIES_AVAILABLE = False

try:
    from ai_ml.mlops import MLOpsManager, initialize_mlops
    MLOPS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MLOps not available: {e}")
    MLOPS_AVAILABLE = False

class MLModelType:
    """ML Model type constants"""
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    HYBRID = "hybrid"
    TIMESERIES = "timeseries"
    ENSEMBLE = "ensemble"

class MLService:
    """
    Unified ML Service for trading signal enhancement
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize ML Service
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configuration from environment variables with defaults
        self.use_ml_predictions = self._get_bool_env('USE_ML_PREDICTIONS', True)
        self.ml_model_path = os.getenv('ML_MODEL_PATH', './ml_models')
        self.retrain_schedule = os.getenv('RETRAIN_SCHEDULE', 'daily')  # daily, weekly, hourly
        self.ml_confidence_threshold = float(os.getenv('ML_CONFIDENCE_THRESHOLD', '0.6'))
        self.ml_model_type = os.getenv('ML_MODEL_TYPE', 'ensemble').lower()
        
        # MLflow configuration
        self.mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 
                                           'file:///home/ubuntu/godmode-quant-orchestrator/mlruns')
        self.mlflow_experiment_name = os.getenv('MLFLOW_EXPERIMENT_NAME', 
                                              'godmode-quant-trading-ml')
        
        # Initialize components
        self.models = {}
        self.mlops_manager = None
        self.experiment_tracker = None
        self.last_retrain = None
        self.is_initialized = False
        
        # Performance tracking
        self.prediction_history = []
        self.performance_metrics = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'avg_confidence': 0.0,
            'last_prediction_time': None
        }
        
        # Initialize if ML is enabled
        if self.use_ml_predictions:
            self._initialize_ml_service()
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable"""
        val = os.getenv(key, str(default)).lower()
        return val in ('true', '1', 'yes', 'on')
    
    def _initialize_ml_service(self):
        """Initialize ML service components"""
        try:
            self.logger.info("Initializing ML Service...")
            
            # Initialize MLOps if available
            if MLOPS_AVAILABLE:
                try:
                    self.mlops_manager, self.experiment_tracker = initialize_mlops(
                        tracking_uri=self.mlflow_tracking_uri,
                        experiment_name=self.mlflow_experiment_name
                    )
                    self.logger.info("MLOps initialized successfully")
                except Exception as e:
                    self.logger.warning(f"MLOps initialization failed: {e}")
                    self.mlops_manager = None
                    self.experiment_tracker = None
            
            # Initialize ML models based on type
            self._initialize_models()
            
            self.is_initialized = True
            self.logger.info("ML Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ML Service: {e}")
            self.is_initialized = False
            # Don't raise - allow fallback to traditional methods
    
    def _initialize_models(self):
        """Initialize ML models based on configuration"""
        try:
            model_type = self.ml_model_type
            
            if model_type in [MLModelType.LSTM, MLModelType.ENSEMBLE] and LSTM_AVAILABLE:
                self.models['lstm'] = LSTMSignalGenerator(
                    sequence_length=int(os.getenv('LSTM_SEQUENCE_LENGTH', '60')),
                    lstm_units=int(os.getenv('LSTM_UNITS', '128')),
                    confidence_threshold=self.ml_confidence_threshold
                )
                self.logger.info("LSTM model initialized")
            
            if model_type in [MLModelType.TRANSFORMER, MLModelType.HYBRID, MLModelType.ENSEMBLE] and TRANSFORMER_AVAILABLE:
                self.models['transformer'] = TransformerPricePredictor(
                    sequence_length=int(os.getenv('TRANSFORMER_SEQUENCE_LENGTH', '60')),
                    num_heads=int(os.getenv('TRANSFORMER_HEADS', '4')),
                    embed_dim=int(os.getenv('TRANSFORMER_EMBED_DIM', '128')),
                    ff_dim=int(os.getenv('TRANSFORMER_FF_DIM', '256')),
                    num_layers=int(os.getenv('TRANSFORMER_LAYERS', '3')),
                    dropout_rate=float(os.getenv('TRANSFORMER_DROPOUT', '0.1')),
                    learning_rate=float(os.getenv('TRANSFORMER_LR', '0.0001'))
                )
                self.logger.info("Transformer model initialized")
                
                # Hybrid model if requested
                if model_type == MLModelType.HYBRID or model_type == MLModelType.ENSEMBLE:
                    self.models['hybrid'] = HybridPredictor(
                        sequence_length=int(os.getenv('HYBRID_SEQUENCE_LENGTH', '60')),
                        lstm_units=int(os.getenv('HYBRID_LSTM_UNITS', '64')),
                        transformer_heads=int(os.getenv('HYBRID_TRANSFORMER_HEADS', '4')),
                        embed_dim=int(os.getenv('HYBRID_EMBED_DIM', '64'))
                    )
                    self.logger.info("Hybrid model initialized")
            
            if model_type in [MLModelType.TIMESERIES, MLModelType.ENSEMBLE] and TIMESERIES_AVAILABLE:
                self.models['timeseries'] = TimeSeriesForecaster(
                    model_type=os.getenv('TIMESERIES_MODEL_TYPE', 'random_forest')
                )
                self.logger.info("Time series model initialized")
                
                # Enhanced MA Crossover strategy
                self.models['enhanced_ma'] = EnhancedMaCrossoverStrategy(
                    fast_ma_length=int(os.getenv('ENHANCED_MA_FAST', '10')),
                    slow_ma_length=int(os.getenv('ENHANCED_MA_SLOW', '30')),
                    prediction_lookback=int(os.getenv('ENHANCED_MA_LOOKBACK', '20')),
                    confidence_threshold=self.ml_confidence_threshold
                )
                self.logger.info("Enhanced MA Crossover strategy initialized")
            
            if not self.models:
                self.logger.warning("No ML models were initialized - falling back to traditional methods")
                
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {e}")
            # Continue with whatever models were successfully initialized
    
    def should_retrain(self) -> bool:
        """Check if models should be retrained based on schedule"""
        if not self.is_initialized or not self.use_ml_predictions:
            return False
            
        if self.last_retrain is None:
            return True
            
        now = datetime.now()
        if self.retrain_schedule == 'hourly':
            return (now - self.last_retrain).total_seconds() > 3600
        elif self.retrain_schedule == 'daily':
            return (now - self.last_retrain).days >= 1
        elif self.retrain_schedule == 'weekly':
            return (now - self.last_retrain).days >= 7
        
        return False
    
    def train_models(self, price_data: np.ndarray, volume_data: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Train all available ML models
        
        Args:
            price_data: Historical price data
            volume_data: Optional volume data
            
        Returns:
            Training results dictionary
        """
        if not self.is_initialized or not self.use_ml_predictions:
            return {'status': 'skipped', 'reason': 'ML disabled or not initialized'}
        
        if len(price_data) < 50:  # Minimum data requirement
            return {'status': 'skipped', 'reason': 'Insufficient training data'}
        
        results = {}
        self.logger.info("Starting ML model training...")
        
        try:
            # Start MLflow run if available
            run = None
            if self.mlops_manager and self.mlops_manager.enabled:
                run = self.mlops_manager.start_run(
                    run_name=f"ml_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    tags={
                        'model_type': self.ml_model_type,
                        'data_points': len(price_data),
                        'training_type': 'scheduled' if self.last_retrain else 'initial'
                    }
                )
                
                # Log training parameters
                if run:
                    self.mlops_manager.log_params({
                        'training_data_points': len(price_data),
                        'retrain_schedule': self.retrain_schedule,
                        'ml_model_type': self.ml_model_type,
                        'confidence_threshold': self.ml_confidence_threshold
                    })
            
            # Train each model
            for model_name, model in self.models.items():
                try:
                    self.logger.info(f"Training {model_name} model...")
                    
                    if hasattr(model, 'fit'):
                        # For LSTM, Transformer, TimeSeries forecasters
                        if model_name in ['lstm', 'transformer']:
                            # These expect price data directly
                            history = model.fit(price_data, 
                                              epochs=int(os.getenv(f'{model_name.upper()}_EPOCHS', '30')),
                                              verbose=0)
                            results[model_name] = {
                                'status': 'success',
                                'epochs_trained': len(history.history['loss']) if history else 0,
                                'final_loss': history.history['loss'][-1] if history and 'loss' in history.history else None
                            }
                        elif model_name == 'hybrid':
                            # Hybrid model training
                            model.fit(price_data, 
                                    epochs=int(os.getenv('HYBRID_EPOCHS', '30')),
                                    verbose=0)
                            results[model_name] = {'status': 'success'}
                        elif model_name == 'timeseries':
                            # Time series forecaster
                            lookback = int(os.getenv('TIMESERIES_LOOKBACK', '10'))
                            model.fit(price_data, lookback=lookback)
                            results[model_name] = {'status': 'success'}
                        elif model_name == 'enhanced_ma':
                            # Enhanced MA strategy (doesn't need explicit training in this context)
                            results[model_name] = {'status': 'success', 'note': 'Strategy ready'}
                    
                    self.logger.info(f"{model_name} model training completed")
                    
                except Exception as e:
                    self.logger.error(f"Failed to train {model_name} model: {e}")
                    results[model_name] = {'status': 'failed', 'error': str(e)}
            
            # End MLflow run
            if run and self.mlops_manager:
                # Log final metrics
                metrics = {
                    'models_trained': len([r for r in results.values() if r.get('status') == 'success']),
                    'models_failed': len([r for r in results.values() if r.get('status') == 'failed']),
                    'training_data_size': len(price_data)
                }
                self.mlops_manager.log_metrics(metrics)
                self.mlops_manager.end_run()
            
            self.last_retrain = datetime.now()
            self.logger.info("ML model training completed")
            
            return {
                'status': 'completed',
                'models': results,
                'timestamp': self.last_retrain.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ML training failed: {e}")
            if run and self.mlops_manager:
                self.mlops_manager.end_run(status="FAILED")
            return {'status': 'failed', 'error': str(e)}
    
    def get_ml_prediction(self, price_data: np.ndarray, 
                         volume_data: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Get ML-enhanced prediction/trading signal
        
        Args:
            price_data: Historical price data
            volume_data: Optional volume data
            
        Returns:
            Prediction dictionary with signal, confidence, and metadata
        """
        # Return default if ML is disabled or not initialized
        if not self.use_ml_predictions or not self.is_initialized:
            return self._get_default_prediction()
        
        # Check if we have enough data
        min_data_points = 50
        if len(price_data) < min_data_points:
            self.logger.warning(f"Insufficient data for ML prediction: {len(price_data)} < {min_data_points}")
            return self._get_default_prediction()
        
        try:
            # Retrain if needed
            if self.should_retrain():
                self.logger.info("Retraining ML models...")
                self.train_models(price_data, volume_data)
            
            # Get predictions from available models
            predictions = {}
            confidences = []
            
            for model_name, model in self.models.items():
                try:
                    pred_result = self._get_model_prediction(model, model_name, price_data, volume_data)
                    if pred_result and pred_result.get('signal') is not None:
                        predictions[model_name] = pred_result
                        if pred_result.get('confidence') is not None:
                            confidences.append(pred_result['confidence'])
                except Exception as e:
                    self.logger.warning(f"Error getting prediction from {model_name}: {e}")
            
            # Ensemble prediction if we have multiple models
            if len(predictions) > 1 and self.ml_model_type == MLModelType.ENSEMBLE:
                final_prediction = self._ensemble_predict(predictions)
            elif len(predictions) == 1:
                # Single model prediction
                model_name = list(predictions.keys())[0]
                final_prediction = predictions[model_name]
            else:
                # No valid predictions
                final_prediction = self._get_default_prediction()
            
            # Update performance metrics
            self._update_performance_metrics(final_prediction)
            
            # Log to MLflow if available
            if self.mlops_manager and self.mlops_manager.enabled and self.experiment_tracker:
                try:
                    # Log prediction as part of current experiment or start a prediction tracking run
                    pass  # Implementation would go here for production
                except Exception as e:
                    self.logger.debug(f"MLflow logging failed: {e}")
            
            return final_prediction
            
        except Exception as e:
            self.logger.error(f"ML prediction failed: {e}")
            return self._get_default_prediction()
    
    def _get_model_prediction(self, model: Any, model_name: str, 
                            price_data: np.ndarray, 
                            volume_data: Optional[np.ndarray]) -> Optional[Dict[str, Any]]:
        """Get prediction from a specific model"""
        try:
            if model_name == 'lstm' and hasattr(model, 'generate_signal'):
                # LSTMSignalGenerator
                result = model.generate_signal(price_data)
                return {
                    'signal': result['signal'],  # -1, 0, 1
                    'confidence': result['confidence'],
                    'predicted_price': result['predicted_price'],
                    'expected_change': result['expected_change'],
                    'model_type': 'lstm'
                }
            
            elif model_name == 'transformer' and hasattr(model, 'predict'):
                # TransformerPricePredictor
                prediction = model.predict(price_data)
                current_price = price_data[-1] if len(price_data) > 0 else 0
                expected_change = (prediction - current_price) / current_price if current_price != 0 else 0
                
                # Convert to signal
                signal = 0
                confidence = 0.5  # Default confidence for transformer
                if expected_change > 0.01:  # 1% threshold
                    signal = 1
                elif expected_change < -0.01:
                    signal = -1
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'predicted_price': float(prediction),
                    'expected_change': float(expected_change),
                    'model_type': 'transformer'
                }
            
            elif model_name == 'hybrid' and hasattr(model, 'predict'):
                # HybridPredictor
                prediction = model.predict(price_data)
                current_price = price_data[-1] if len(price_data) > 0 else 0
                expected_change = (prediction - current_price) / current_price if current_price != 0 else 0
                
                # Simple confidence based on recent performance
                confidence = 0.6  # Placeholder - would be calculated from validation
                
                # Convert to signal
                signal = 0
                if expected_change > 0.01:
                    signal = 1
                elif expected_change < -0.01:
                    signal = -1
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'predicted_price': float(prediction),
                    'expected_change': float(expected_change),
                    'model_type': 'hybrid'
                }
            
            elif model_name == 'timeseries' and hasattr(model, 'predict'):
                # TimeSeriesForecaster
                prediction = model.predict(price_data)
                if prediction is None:
                    return None
                    
                current_price = price_data[-1] if len(price_data) > 0 else 0
                expected_change = (prediction - current_price) / current_price if current_price != 0 else 0
                
                # Simple confidence
                confidence = 0.5
                
                # Convert to signal
                signal = 0
                if expected_change > 0.01:
                    signal = 1
                elif expected_change < -0.01:
                    signal = -1
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'predicted_price': float(prediction),
                    'expected_change': float(expected_change),
                    'model_type': 'timeseries'
                }
            
            elif model_name == 'enhanced_ma' and hasattr(model, 'generate_signal'):
                # EnhancedMaCrossoverStrategy
                result = model.generate_signal(price_data)
                return {
                    'signal': result['signal'],
                    'confidence': result.get('prediction_confidence', 0.5),
                    'predicted_price': result.get('price_prediction'),
                    'expected_change': ((result.get('price_prediction', 0) - price_data[-1]) / price_data[-1] 
                                      if result.get('price_prediction') and price_data[-1] != 0 else 0),
                    'model_type': 'enhanced_ma',
                    'reasoning': result.get('reasoning', [])
                }
            
        except Exception as e:
            self.logger.debug(f"Model {model_name} prediction error: {e}")
            return None
        
        return None
    
    def _ensemble_predict(self, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """Create ensemble prediction from multiple models"""
        try:
            # Weighted voting based on confidence
            weighted_signal = 0.0
            total_confidence = 0.0
            predicted_prices = []
            expected_changes = []
            
            for model_name, pred in predictions.items():
                confidence = pred.get('confidence', 0.5)
                signal = pred.get('signal', 0)
                
                weighted_signal += signal * confidence
                total_confidence += confidence
                
                if pred.get('predicted_price') is not None:
                    predicted_prices.append(pred['predicted_price'])
                if pred.get('expected_change') is not None:
                    expected_changes.append(pred['expected_change'])
            
            # Calculate final signal
            final_signal = 0
            if total_confidence > 0:
                avg_signal = weighted_signal / total_confidence
                if avg_signal > 0.3:
                    final_signal = 1
                elif avg_signal < -0.3:
                    final_signal = -1
            
            # Calculate average confidence
            avg_confidence = total_confidence / len(predictions) if predictions else 0.5
            
            # Calculate ensemble prediction values
            avg_predicted_price = np.mean(predicted_prices) if predicted_prices else None
            avg_expected_change = np.mean(expected_changes) if expected_changes else 0.0
            
            return {
                'signal': final_signal,
                'confidence': min(avg_confidence, 1.0),  # Cap at 1.0
                'predicted_price': avg_predicted_price,
                'expected_change': avg_expected_change,
                'model_type': 'ensemble',
                'models_used': list(predictions.keys()),
                'individual_predictions': predictions
            }
            
        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            return self._get_default_prediction()
    
    def _get_default_prediction(self) -> Dict[str, Any]:
        """Return default prediction when ML is not available"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'predicted_price': None,
            'expected_change': 0.0,
            'model_type': 'none',
            'reason': 'ML disabled or unavailable'
        }
    
    def _update_performance_metrics(self, prediction: Dict[str, Any]):
        """Update internal performance metrics"""
        self.performance_metrics['total_predictions'] += 1
        if prediction.get('confidence', 0) > 0:
            self.performance_metrics['successful_predictions'] += 1
        
        # Update rolling average confidence
        confidence = prediction.get('confidence', 0)
        total = self.performance_metrics['total_predictions']
        current_avg = self.performance_metrics['avg_confidence']
        self.performance_metrics['avg_confidence'] = (
            (current_avg * (total - 1) + confidence) / total
        )
        
        self.performance_metrics['last_prediction_time'] = datetime.now().isoformat()
        
        # Keep history for drift detection (last 100 predictions)
        self.prediction_history.append({
            'timestamp': datetime.now().isoformat(),
            'prediction': prediction
        })
        if len(self.prediction_history) > 100:
            self.prediction_history.pop(0)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get ML service performance metrics"""
        return {
            **self.performance_metrics,
            'models_available': list(self.models.keys()),
            'ml_enabled': self.use_ml_predictions,
            'ml_initialized': self.is_initialized,
            'last_retrain': self.last_retrain.isoformat() if self.last_retrain else None,
            'should_retrain': self.should_retrain()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get ML service status"""
        return {
            'service': 'ML Service',
            'status': 'initialized' if self.is_initialized else 'not_initialized',
            'ml_enabled': self.use_ml_predictions,
            'model_type': self.ml_model_type,
            'models_loaded': list(self.models.keys()),
            'performance': self.get_performance_metrics()
        }

# Global ML service instance
_ml_service: Optional[MLService] = None

def get_ml_service() -> Optional[MLService]:
    """Get the global ML service instance"""
    return _ml_service

def initialize_ml_service(config: Dict = None) -> MLService:
    """Initialize and return the global ML service"""
    global _ml_service
    _ml_service = MLService(config)
    return _ml_service
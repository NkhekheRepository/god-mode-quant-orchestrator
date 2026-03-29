"""
ML Services Tests for GodMode Quant Orchestrator
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestTimeSeriesForecast(unittest.TestCase):
    """Test time series forecasting module"""
    
    def test_forecaster_initialization(self):
        """Test TimeSeriesForecaster initialization"""
        from ai_ml.time_series_forecast import TimeSeriesForecaster
        
        # Test linear model initialization
        forecaster = TimeSeriesForecaster(model_type='linear')
        self.assertEqual(forecaster.model_type, 'linear')
        self.assertIsNotNone(forecaster.model)
        self.assertIsNotNone(forecaster.scaler)
        self.assertFalse(forecaster.is_fitted)
        
        # Test random forest initialization
        forecaster_rf = TimeSeriesForecaster(model_type='random_forest')
        self.assertEqual(forecaster_rf.model_type, 'random_forest')
        self.assertIsNotNone(forecaster_rf.model)
        
        # Test invalid model type raises error
        with self.assertRaises(ValueError):
            TimeSeriesForecaster(model_type='invalid')
    
    def test_forecaster_fit_predict(self):
        """Test fitting and prediction"""
        from ai_ml.time_series_forecast import TimeSeriesForecaster
        
        # Generate sample time series data
        np.random.seed(42)
        data = np.cumsum(np.random.randn(100)) + 50  # Random walk
        
        forecaster = TimeSeriesForecaster(model_type='linear')
        
        # Fit the model
        forecaster.fit(data, lookback=10)
        self.assertTrue(forecaster.is_fitted)
        
        # Make prediction
        prediction = forecaster.predict(data, lookback=10)
        self.assertIsNotNone(prediction)
        self.assertIsInstance(prediction, (float, np.floating))
        
        # Test prediction with insufficient data
        short_data = data[:5]
        prediction_short = forecaster.predict(short_data, lookback=10)
        self.assertIsNone(prediction_short)
        
        # Test predict_multiple
        predictions = forecaster.predict_multiple(data, steps=3, lookback=10)
        self.assertEqual(len(predictions), 3)
        for pred in predictions:
            self.assertIsNotNone(pred)
            self.assertIsInstance(pred, (float, np.floating))
    
    def test_enhanced_ma_crossover(self):
        """Test EnhancedMaCrossoverStrategy"""
        from ai_ml.time_series_forecast import EnhancedMaCrossoverStrategy
        
        # Generate sample price data
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)  # Price series
        
        strategy = EnhancedMaCrossoverStrategy(
            fast_ma_length=5,
            slow_ma_length=15,
            prediction_lookback=20,
            confidence_threshold=0.6
        )
        
        # Generate signal
        result = strategy.generate_signal(prices)
        
        # Check result structure
        self.assertIn('signal', result)
        self.assertIn('reasoning', result)
        self.assertIn('fast_ma', result)
        self.assertIn('slow_ma', result)
        self.assertIn('price_prediction', result)
        self.assertIn('prediction_confidence', result)
        self.assertIn('ma_trend', result)
        
        # Check signal values
        self.assertIn(result['signal'], [-1, 0, 1])
        self.assertIsInstance(result['reasoning'], list)
        self.assertIsInstance(result['fast_ma'], float)
        self.assertIsInstance(result['slow_ma'], float)
        self.assertIsInstance(result['ma_trend'], int)
        
        # Test with insufficient data (should still work with defaults)
        short_prices = prices[:10]
        result_short = strategy.generate_signal(short_prices)
        self.assertIn('signal', result_short)
        self.assertIn('reasoning', result_short)
    
    def test_forecaster_prepare_features(self):
        """Test feature preparation method"""
        from ai_ml.time_series_forecast import TimeSeriesForecaster
        
        forecaster = TimeSeriesForecaster(model_type='linear')
        
        # Test with sample data
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        X, y = forecaster.prepare_features(data, lookback=3)
        
        # Check shapes
        self.assertEqual(X.shape[0], 7)  # 10 - 3 = 7 samples
        self.assertEqual(X.shape[1], 3)  # lookback window
        self.assertEqual(y.shape[0], 7)
        
        # Check values
        np.testing.assert_array_equal(X[0], [1, 2, 3])
        self.assertEqual(y[0], 4)
        np.testing.assert_array_equal(X[1], [2, 3, 4])
        self.assertEqual(y[1], 5)


class TestSentimentAnalysis(unittest.TestCase):
    """Test sentiment analysis module"""
    
    def test_sentiment_analyzer_initialization(self):
        """Test SentimentAnalyzer initialization"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        self.assertIsNotNone(analyzer.positive_words)
        self.assertIsNotNone(analyzer.negative_words)
        self.assertIsNotNone(analyzer.amplifiers)
        self.assertIsNotNone(analyzer.diminishers)
        
        # Check that lexicons are sets
        self.assertIsInstance(analyzer.positive_words, set)
        self.assertIsInstance(analyzer.negative_words, set)
        self.assertGreater(len(analyzer.positive_words), 0)
        self.assertGreater(len(analyzer.negative_words), 0)
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        # Test positive text
        positive_text = "The market is bullish and prices are rising significantly"
        result = analyzer.analyze_sentiment(positive_text)
        
        self.assertIn('positive', result)
        self.assertIn('negative', result)
        self.assertIn('neutral', result)
        self.assertIn('compound', result)
        
        self.assertGreater(result['positive'], result['negative'])
        self.assertGreater(result['compound'], 0)
        
        # Test with amplifier
        positive_amplified = "The market is extremely bullish"
        result_amp = analyzer.analyze_sentiment(positive_amplified)
        self.assertGreater(result_amp['positive'], 0)
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        # Test negative text
        negative_text = "The market is bearish and prices are dropping sharply"
        result = analyzer.analyze_sentiment(negative_text)
        
        self.assertGreater(result['negative'], result['positive'])
        self.assertLess(result['compound'], 0)
        
        # Test with diminisher
        negative_diminished = "The market is slightly bearish"
        result_dim = analyzer.analyze_sentiment(negative_diminished)
        self.assertGreater(result_dim['negative'], 0)
    
    def test_batch_analysis(self):
        """Test batch sentiment analysis"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        # Test batch of texts
        texts = [
            "Bullish market with rising prices",
            "Bearish sentiment with declining values",
            "Neutral market conditions"
        ]
        
        result = analyzer.analyze_batch(texts)
        
        self.assertIn('positive', result)
        self.assertIn('negative', result)
        self.assertIn('neutral', result)
        self.assertIn('compound', result)
        
        # Check that scores are averages
        individual_results = [analyzer.analyze_sentiment(text) for text in texts]
        expected_positive = np.mean([r['positive'] for r in individual_results])
        expected_negative = np.mean([r['negative'] for r in individual_results])
        
        self.assertAlmostEqual(result['positive'], expected_positive, places=5)
        self.assertAlmostEqual(result['negative'], expected_negative, places=5)
        
        # Test empty batch
        empty_result = analyzer.analyze_batch([])
        self.assertEqual(empty_result['compound'], 0.0)
    
    def test_market_signal(self):
        """Test market signal generation from sentiment scores"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        # Test positive signal
        signal, reasoning = analyzer.get_market_signal(0.5, threshold=0.2)
        self.assertEqual(signal, 1)
        self.assertIn("Positive", reasoning)
        
        # Test negative signal
        signal, reasoning = analyzer.get_market_signal(-0.5, threshold=0.2)
        self.assertEqual(signal, -1)
        self.assertIn("Negative", reasoning)
        
        # Test neutral signal
        signal, reasoning = analyzer.get_market_signal(0.1, threshold=0.2)
        self.assertEqual(signal, 0)
        self.assertIn("Neutral", reasoning)
    
    def test_preprocess_text(self):
        """Test text preprocessing"""
        from ai_ml.sentiment_analysis import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        text = "Hello! This is a TEST with 123 numbers and SPECIAL characters."
        cleaned = analyzer.preprocess_text(text)
        
        self.assertEqual(cleaned, "hello this is a test with numbers and special characters")
        
        # Test with extra whitespace
        text_extra = "  Multiple   spaces   between   words  "
        cleaned_extra = analyzer.preprocess_text(text_extra)
        self.assertEqual(cleaned_extra, "multiple spaces between words")


class TestLSTMForecastPyTorch(unittest.TestCase):
    """Test LSTM PyTorch forecasting"""
    
    @classmethod
    def setUpClass(cls):
        """Check PyTorch availability"""
        try:
            import torch
            cls.torch_available = True
        except ImportError:
            cls.torch_available = False
    
    def test_lstm_import(self):
        """Test LSTM module imports without error"""
        from ai_ml.lstm_forecast_pytorch import LSTMPricePredictor, LSTMSignalGenerator
        
        self.assertTrue(self.torch_available, "PyTorch not available")
        
        # Check that classes exist
        self.assertIsNotNone(LSTMPricePredictor)
        self.assertIsNotNone(LSTMSignalGenerator)
    
    def test_lstm_initialization(self):
        """Test LSTM predictor initialization"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        from ai_ml.lstm_forecast_pytorch import LSTMPricePredictor
        
        predictor = LSTMPricePredictor(
            sequence_length=30,
            lstm_units=64,
            dropout_rate=0.1,
            learning_rate=0.001,
            bidirectional=True
        )
        
        self.assertEqual(predictor.sequence_length, 30)
        self.assertEqual(predictor.lstm_units, 64)
        self.assertEqual(predictor.dropout_rate, 0.1)
        self.assertEqual(predictor.learning_rate, 0.001)
        self.assertTrue(predictor.bidirectional)
        self.assertFalse(predictor.is_fitted)
        self.assertIsNotNone(predictor.device)
    
    def test_lstm_fit_predict(self):
        """Test LSTM model fitting and prediction"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        from ai_ml.lstm_forecast_pytorch import LSTMPricePredictor
        
        # Generate sample price data
        np.random.seed(42)
        price_data = 100 + np.cumsum(np.random.randn(200) * 2)  # Random walk
        
        predictor = LSTMPricePredictor(
            sequence_length=20,
            lstm_units=32,
            dropout_rate=0.0,
            learning_rate=0.01,
            bidirectional=False
        )
        
        # Fit model (few epochs for speed)
        history = predictor.fit(price_data, epochs=5, batch_size=16, verbose=0)
        
        self.assertTrue(predictor.is_fitted)
        self.assertIn('loss', history)
        self.assertIn('mae', history)
        self.assertEqual(len(history['loss']), 5)
        
        # Make prediction
        prediction = predictor.predict(price_data)
        self.assertIsInstance(prediction, float)
        
        # Test signal generation
        signal_result = predictor.generate_signal(price_data)
        self.assertIn('signal', signal_result)
        self.assertIn('confidence', signal_result)
        self.assertIn('predicted_price', signal_result)
        self.assertIn('expected_change', signal_result)
        self.assertIn(signal_result['signal'], [-1, 0, 1])
        self.assertIsInstance(signal_result['confidence'], float)
        
        # Test statistics
        stats = predictor.get_statistics()
        self.assertEqual(stats['model_type'], 'lstm_pytorch')
        self.assertEqual(stats['sequence_length'], 20)
        self.assertTrue(stats['is_fitted'])


class TestTransformerForecastPyTorch(unittest.TestCase):
    """Test Transformer PyTorch forecasting"""
    
    @classmethod
    def setUpClass(cls):
        """Check PyTorch availability"""
        try:
            import torch
            cls.torch_available = True
        except ImportError:
            cls.torch_available = False
    
    def test_transformer_import(self):
        """Test Transformer module imports without error"""
        from ai_ml.transformer_forecast_pytorch import (
            TransformerPricePredictor, 
            HybridPredictor,
            TransformerModel,
            PositionalEncoding,
            TransformerBlock
        )
        
        self.assertTrue(self.torch_available, "PyTorch not available")
        
        # Check that classes exist
        self.assertIsNotNone(TransformerPricePredictor)
        self.assertIsNotNone(HybridPredictor)
        self.assertIsNotNone(TransformerModel)
        self.assertIsNotNone(PositionalEncoding)
        self.assertIsNotNone(TransformerBlock)
    
    def test_transformer_initialization(self):
        """Test Transformer predictor initialization"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        from ai_ml.transformer_forecast_pytorch import TransformerPricePredictor
        
        predictor = TransformerPricePredictor(
            sequence_length=40,
            num_heads=4,
            embed_dim=64,
            ff_dim=128,
            num_layers=2,
            dropout_rate=0.05,
            learning_rate=0.0001
        )
        
        self.assertEqual(predictor.sequence_length, 40)
        self.assertEqual(predictor.num_heads, 4)
        self.assertEqual(predictor.embed_dim, 64)
        self.assertEqual(predictor.ff_dim, 128)
        self.assertEqual(predictor.num_layers, 2)
        self.assertEqual(predictor.dropout_rate, 0.05)
        self.assertEqual(predictor.learning_rate, 0.0001)
        self.assertFalse(predictor.is_fitted)
        self.assertIsNotNone(predictor.device)
    
    def test_transformer_fit_predict(self):
        """Test Transformer model fitting and prediction"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        from ai_ml.transformer_forecast_pytorch import TransformerPricePredictor
        
        # Generate sample price data
        np.random.seed(42)
        price_data = 100 + np.cumsum(np.random.randn(150) * 1.5)  # Random walk
        
        predictor = TransformerPricePredictor(
            sequence_length=15,
            num_heads=2,
            embed_dim=32,
            ff_dim=64,
            num_layers=1,
            dropout_rate=0.0,
            learning_rate=0.001
        )
        
        # Fit model (few epochs for speed)
        history = predictor.fit(price_data, epochs=5, batch_size=16, verbose=0)
        
        self.assertTrue(predictor.is_fitted)
        self.assertIn('loss', history)
        self.assertIn('mae', history)
        self.assertEqual(len(history['loss']), 5)
        
        # Make prediction
        prediction = predictor.predict(price_data)
        self.assertIsInstance(prediction, float)
        
        # Test signal generation
        signal_result = predictor.generate_signal(price_data)
        self.assertIn('signal', signal_result)
        self.assertIn('confidence', signal_result)
        self.assertIn('predicted_price', signal_result)
        self.assertIn('expected_change', signal_result)
        self.assertIn(signal_result['signal'], [-1, 0, 1])
        self.assertIsInstance(signal_result['confidence'], float)
        
        # Test statistics
        stats = predictor.get_statistics()
        self.assertEqual(stats['model_type'], 'transformer_pytorch')
        self.assertEqual(stats['sequence_length'], 15)
        self.assertTrue(stats['is_fitted'])
    
    def test_hybrid_predictor(self):
        """Test Hybrid predictor combining LSTM and Transformer"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        from ai_ml.transformer_forecast_pytorch import HybridPredictor
        
        # Generate sample price data
        np.random.seed(42)
        price_data = 100 + np.cumsum(np.random.randn(100) * 1)
        
        hybrid = HybridPredictor(
            sequence_length=20,
            lstm_units=32,
            transformer_heads=2,
            embed_dim=32
        )
        
        # Fit both models
        history = hybrid.fit(price_data, epochs=3, verbose=0)
        
        self.assertTrue(hybrid.is_fitted)
        self.assertIn('lstm', history)
        self.assertIn('transformer', history)
        
        # Test ensemble prediction
        prediction = hybrid.predict(price_data)
        self.assertIsInstance(prediction, float)
        
        # Verify prediction is weighted average
        lstm_pred = hybrid.lstm_predictor.predict(price_data)
        transformer_pred = hybrid.transformer_predictor.predict(price_data)
        expected = 0.4 * lstm_pred + 0.6 * transformer_pred
        self.assertAlmostEqual(prediction, expected, places=5)
    
    def test_positional_encoding(self):
        """Test PositionalEncoding module"""
        if not self.torch_available:
            self.skipTest("PyTorch not available")
        
        import torch
        from ai_ml.transformer_forecast_pytorch import PositionalEncoding
        
        # Test initialization
        pe = PositionalEncoding(d_model=64, max_len=100)
        self.assertEqual(pe.pe.shape, (1, 100, 64))
        
        # Test forward pass
        x = torch.randn(2, 30, 64)  # batch=2, seq_len=30, d_model=64
        output = pe(x)
        self.assertEqual(output.shape, x.shape)
        
        # Output should be input + positional encoding
        expected = x + pe.pe[:, :30, :]
        torch.testing.assert_close(output, expected)


if __name__ == '__main__':
    unittest.main()
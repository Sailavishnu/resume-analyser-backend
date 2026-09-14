"""
ML Model predictor for Resume-Job Match scoring.

Loads the trained model and provides prediction interface.
"""
import os
import json
import joblib
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.config import settings
from app.ml.feature_extractor import ResumeJobFeatureExtractor


class ResumeJobMatchPredictor:
    """
    Loads and serves the trained Resume-Job Match ML model.
    Thread-safe singleton for use across the FastAPI application.
    """
    
    _instance: Optional['ResumeJobMatchPredictor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        
        self.model = None
        self.metadata = None
        self.feature_extractor = ResumeJobFeatureExtractor()
        self._initialized = False
    
    def load_model(self, force_reload: bool = False) -> None:
        """
        Load the trained model and metadata.
        Call once at application startup, or force_reload=True to refresh.
        """
        if self._initialized and not force_reload:
            return
        
        model_path = Path(settings.ML_MODEL_PATH)
        metadata_path = model_path.parent / "model_metadata.json"
        
        # Check if model exists
        if not model_path.exists():
            raise FileNotFoundError(
                f"ML model not found at {model_path}. "
                f"Train the model first: python ml/train_model.py"
            )
        
        if not metadata_path.exists():
            raise FileNotFoundError(f"Model metadata not found at {metadata_path}")
        
        # Load model
        self.model = joblib.load(model_path)
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        # Validate feature compatibility
        expected_features = self.feature_extractor.feature_names
        model_features = self.metadata['features']
        
        if expected_features != model_features:
            raise ValueError(
                f"Feature mismatch! Expected: {expected_features}, "
                f"Model trained with: {model_features}"
            )
        
        self._initialized = True
        
        print(f"✅ ML model loaded: {self.metadata['model_type']} v{self.metadata['version']}")
        print(f"   Trained: {self.metadata['trained_at']}")
        print(f"   Performance: R²={self.metadata['evaluation_metrics']['r2']}")
    
    def predict_match_score(self, resume_data: dict, job_data: dict) -> Dict[str, Any]:
        """
        Predict resume-job match score using the trained ML model.
        
        Args:
            resume_data: Resume document from MongoDB (with parsed_data)
            job_data: Job document from MongoDB
            
        Returns:
            {
                'overall_score': float (0-100),
                'display_score': int (rounded),
                'model_version': str,
                'features': dict,
                'confidence': float
            }
        """
        if not self._initialized:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Extract features
        features = self.feature_extractor.extract_features(resume_data, job_data)
        
        # Predict
        raw_prediction = self.model.predict(features.reshape(1, -1))[0]
        
        # Clamp to valid range (safety boundary)
        clamped_score = np.clip(raw_prediction, 0.0, 100.0)
        
        # Feature breakdown for transparency
        feature_dict = {
            name: float(value) 
            for name, value in zip(self.feature_extractor.feature_names, features)
        }
        
        # Confidence estimation (simplified)
        # Higher confidence when features are in expected ranges
        confidence = self._estimate_confidence(features)
        
        return {
            'overall_score': float(clamped_score),
            'display_score': int(round(clamped_score)),
            'model_version': self.metadata['version'],
            'features': feature_dict,
            'confidence': confidence
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata for debugging/admin purposes."""
        if not self._initialized:
            return {'error': 'Model not loaded'}
        
        return {
            'model_type': self.metadata['model_type'],
            'version': self.metadata['version'],
            'trained_at': self.metadata['trained_at'],
            'features': self.metadata['features'],
            'metrics': self.metadata['evaluation_metrics'],
            'feature_importance': self.metadata['feature_importance']
        }
    
    def _estimate_confidence(self, features: np.ndarray) -> float:
        """
        Estimate prediction confidence based on feature values.
        
        Higher confidence when features are within typical training ranges.
        This is a simple heuristic - could be improved with proper uncertainty quantification.
        """
        # Expected ranges from training data (rough estimates)
        expected_ranges = [
            (0.4, 0.95),  # skill_overlap
            (0.45, 0.96), # required_skill_coverage
            (0.37, 0.93), # keyword_overlap
            (0.47, 0.96), # experience_similarity
            (0.6, 1.0),   # education_match
            (0.41, 0.94)  # project_relevance
        ]
        
        in_range_count = 0
        for i, (feature_val, (min_val, max_val)) in enumerate(zip(features, expected_ranges)):
            if min_val <= feature_val <= max_val:
                in_range_count += 1
        
        # Confidence based on how many features are in expected ranges
        base_confidence = in_range_count / len(features)
        
        # Boost confidence if features are well-balanced (no extreme outliers)
        feature_std = np.std(features)
        if feature_std < 0.2:  # Well-balanced features
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self._initialized and self.model is not None


# Global predictor instance
predictor = ResumeJobMatchPredictor()
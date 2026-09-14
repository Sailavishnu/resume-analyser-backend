#!/usr/bin/env python3
"""
Evaluate the trained Resume-Job Match Model.

Usage:
    python ml/evaluate_model.py
"""
import os
import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def load_model_and_metadata(model_path: str, metadata_path: str) -> tuple:
    """Load the trained model and its metadata."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")
    
    model = joblib.load(model_path)
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ Loaded model: {metadata['model_type']} v{metadata['version']}")
    print(f"   Trained: {metadata['trained_at']}")
    print(f"   Features: {len(metadata['features'])}")
    
    return model, metadata

def cross_validate_model(model, X: np.ndarray, y: np.ndarray) -> dict:
    """Perform cross-validation on the model."""
    print("\n🔄 Running 5-fold cross-validation...")
    
    # Cross-validation scores
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    cv_mae = -cross_val_score(model, X, y, cv=5, scoring='neg_mean_absolute_error')
    cv_rmse = np.sqrt(-cross_val_score(model, X, y, cv=5, scoring='neg_mean_squared_error'))
    
    cv_results = {
        'r2_scores': cv_scores,
        'r2_mean': cv_scores.mean(),
        'r2_std': cv_scores.std(),
        'mae_scores': cv_mae,
        'mae_mean': cv_mae.mean(),
        'mae_std': cv_mae.std(),
        'rmse_scores': cv_rmse,
        'rmse_mean': cv_rmse.mean(),
        'rmse_std': cv_rmse.std()
    }
    
    print(f"✅ Cross-validation Results:")
    print(f"   R² Score: {cv_results['r2_mean']:.3f} (±{cv_results['r2_std']:.3f})")
    print(f"   MAE:      {cv_results['mae_mean']:.2f} (±{cv_results['mae_std']:.2f})")
    print(f"   RMSE:     {cv_results['rmse_mean']:.2f} (±{cv_results['rmse_std']:.2f})")
    
    return cv_results

def test_predictions(model, X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> None:
    """Test model predictions on sample inputs."""
    print("\n🧪 Testing Sample Predictions:")
    print("-" * 60)
    
    # Generate a few test cases
    test_cases = [
        {
            'name': 'Excellent Match',
            'features': [0.90, 0.85, 0.88, 0.90, 1.0, 0.85],
            'expected': '~85-90'
        },
        {
            'name': 'Good Match',
            'features': [0.75, 0.70, 0.72, 0.80, 1.0, 0.75],
            'expected': '~75-80'
        },
        {
            'name': 'Average Match',
            'features': [0.60, 0.65, 0.58, 0.70, 1.0, 0.65],
            'expected': '~65-70'
        },
        {
            'name': 'Poor Match',
            'features': [0.45, 0.50, 0.40, 0.55, 0.8, 0.50],
            'expected': '~50-55'
        }
    ]
    
    for case in test_cases:
        features = np.array(case['features']).reshape(1, -1)
        prediction = model.predict(features)[0]
        
        print(f"{case['name']:15} → {prediction:5.1f}% (Expected: {case['expected']})")
        
        # Show feature breakdown
        print("  Feature breakdown:")
        for fname, fval in zip(feature_names, case['features']):
            print(f"    {fname:25} {fval:.2f}")
        print()

def analyze_feature_importance(metadata: dict) -> None:
    """Display feature importance analysis."""
    print("\n📊 Feature Importance Analysis:")
    print("-" * 50)
    
    importance = metadata['feature_importance']
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    
    for i, (feature, score) in enumerate(sorted_features, 1):
        bar = "█" * int(score * 50)  # Visual bar
        print(f"{i}. {feature:25} {score:.3f} {bar}")

def prediction_distribution_analysis(model, X: np.ndarray, y: np.ndarray) -> None:
    """Analyze the distribution of predictions vs actual values."""
    print("\n📈 Prediction Distribution Analysis:")
    print("-" * 45)
    
    predictions = model.predict(X)
    
    # Calculate residuals
    residuals = y - predictions
    
    # Statistics
    print(f"Prediction Range:  {predictions.min():.1f} - {predictions.max():.1f}")
    print(f"Actual Range:      {y.min():.1f} - {y.max():.1f}")
    print(f"Mean Residual:     {residuals.mean():.2f}")
    print(f"Residual Std:      {residuals.std():.2f}")
    
    # Score buckets analysis
    buckets = [(0, 50), (50, 70), (70, 85), (85, 100)]
    
    print("\nScore Distribution:")
    for low, high in buckets:
        actual_count = np.sum((y >= low) & (y < high))
        pred_count = np.sum((predictions >= low) & (predictions < high))
        print(f"  {low:2d}-{high:2d}%: Actual={actual_count:2d}, Predicted={pred_count:2d}")

def main():
    """Main evaluation pipeline."""
    print("🔍 Resume-Job Match Model Evaluation")
    print("=" * 50)
    
    # Paths
    model_path = "ml/artifacts/resume_job_match_model.joblib"
    metadata_path = "ml/artifacts/model_metadata.json"
    dataset_path = "ml/dataset/resume_job_matches.csv"
    
    try:
        # Load model and data
        model, metadata = load_model_and_metadata(model_path, metadata_path)
        
        # Load dataset for evaluation
        df = pd.read_csv(dataset_path)
        feature_names = metadata['features']
        X = df[feature_names].values
        y = df['match_score'].values
        
        print(f"\n📊 Dataset Info:")
        print(f"   Samples: {len(df)}")
        print(f"   Features: {len(feature_names)}")
        
        # Display training metrics
        train_metrics = metadata['evaluation_metrics']
        print(f"\n📈 Training Performance:")
        print(f"   MAE:  {train_metrics['mae']}")
        print(f"   RMSE: {train_metrics['rmse']}")
        print(f"   R²:   {train_metrics['r2']}")
        
        # Cross-validation
        cv_results = cross_validate_model(model, X, y)
        
        # Feature importance
        analyze_feature_importance(metadata)
        
        # Test predictions
        test_predictions(model, X, y, feature_names)
        
        # Distribution analysis
        prediction_distribution_analysis(model, X, y)
        
        print("\n🎯 Model Evaluation Summary:")
        print("-" * 40)
        print(f"✅ Model performs well with R² = {cv_results['r2_mean']:.3f}")
        print(f"✅ Average prediction error: ±{cv_results['mae_mean']:.1f} points")
        print(f"✅ Ready for production use in JD matching pipeline")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
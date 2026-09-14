#!/usr/bin/env python3
"""
Train the Resume-Job Match Prediction Model.

Usage:
    python ml/train_model.py
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import json
from datetime import datetime

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate the training dataset."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    
    df = pd.read_csv(dataset_path)
    
    # Validate required columns
    required_cols = [
        'skill_overlap', 'required_skill_coverage', 'keyword_overlap',
        'experience_similarity', 'education_match', 'project_relevance',
        'match_score'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    print(f"✅ Loaded dataset: {len(df)} samples")
    print(f"   Features: {required_cols[:-1]}")
    print(f"   Target: match_score")
    
    return df

def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract features and target variable."""
    feature_columns = [
        'skill_overlap',
        'required_skill_coverage', 
        'keyword_overlap',
        'experience_similarity',
        'education_match',
        'project_relevance'
    ]
    
    X = df[feature_columns].values
    y = df['match_score'].values
    
    print(f"✅ Feature matrix: {X.shape}")
    print(f"   Target vector: {y.shape}")
    print(f"   Score range: {y.min():.1f} - {y.max():.1f}")
    
    return X, y, feature_columns

def train_model(X: np.ndarray, y: np.ndarray) -> tuple[RandomForestRegressor, dict]:
    """Train the Random Forest model and return evaluation metrics."""
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"✅ Data split:")
    print(f"   Training: {X_train.shape[0]} samples")
    print(f"   Testing:  {X_test.shape[0]} samples")
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    
    print("🔄 Training Random Forest Regressor...")
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    metrics = {
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'r2': r2_score(y_test, y_pred),
        'training_samples': len(X_train),
        'test_samples': len(X_test)
    }
    
    print(f"✅ Model Performance:")
    print(f"   MAE:  {metrics['mae']:.2f}")
    print(f"   RMSE: {metrics['rmse']:.2f}")
    print(f"   R²:   {metrics['r2']:.3f}")
    
    return model, metrics

def save_model_artifacts(
    model: RandomForestRegressor,
    metrics: dict,
    feature_names: list[str],
    model_path: str,
    metadata_path: str
) -> None:
    """Save the trained model and metadata."""
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # Save model
    joblib.dump(model, model_path)
    print(f"✅ Model saved: {model_path}")
    
    # Create metadata
    metadata = {
        'model_type': 'RandomForestRegressor',
        'version': '1.0',
        'features': feature_names,
        'trained_at': datetime.now().isoformat(),
        'dataset_size': metrics['training_samples'] + metrics['test_samples'],
        'training_samples': metrics['training_samples'],
        'test_samples': metrics['test_samples'],
        'evaluation_metrics': {
            'mae': round(metrics['mae'], 3),
            'rmse': round(metrics['rmse'], 3),
            'r2': round(metrics['r2'], 3)
        },
        'hyperparameters': {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42
        },
        'feature_importance': {
            name: round(importance, 3) 
            for name, importance in zip(feature_names, model.feature_importances_)
        }
    }
    
    # Save metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Metadata saved: {metadata_path}")
    
    # Print feature importance
    print(f"\n📊 Feature Importance:")
    for name, importance in metadata['feature_importance'].items():
        print(f"   {name:25} {importance:.3f}")

def main():
    """Main training pipeline."""
    print("🚀 Resume-Job Match Model Training")
    print("=" * 50)
    
    # Paths
    dataset_path = "ml/dataset/resume_job_matches.csv"
    model_path = "ml/artifacts/resume_job_match_model.joblib"
    metadata_path = "ml/artifacts/model_metadata.json"
    
    try:
        # Load and prepare data
        df = load_dataset(dataset_path)
        X, y, feature_names = prepare_features(df)
        
        # Train model
        model, metrics = train_model(X, y)
        
        # Save artifacts
        save_model_artifacts(model, metrics, feature_names, model_path, metadata_path)
        
        print("\n🎉 Training completed successfully!")
        print(f"   Model ready for inference at: {model_path}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
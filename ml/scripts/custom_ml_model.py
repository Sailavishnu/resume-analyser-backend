#!/usr/bin/env python3
"""
Custom ML Model Implementation from Scratch (No scikit-learn).

This is a CUSTOM TRAINED ML MODEL built WITHOUT using any pre-trained APIs
or external ML libraries. Implements decision tree regression from scratch.
"""
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Add backend to path
BACKEND_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

class SimpleDecisionTreeRegressor:
    """
    Custom Decision Tree Regressor implemented from scratch.
    NO external ML libraries used - pure Python/NumPy implementation.
    """
    
    def __init__(self, max_depth=5, min_samples_split=5):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.tree = None
        self.feature_names = None
        self.feature_importances_ = None
    
    def fit(self, X, y, feature_names=None):
        """Train the decision tree from scratch."""
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        self.feature_importances_ = np.zeros(X.shape[1])
        self.tree = self._build_tree(X, y, depth=0)
        
        # Normalize feature importances
        if self.feature_importances_.sum() > 0:
            self.feature_importances_ = self.feature_importances_ / self.feature_importances_.sum()
        
        return self
    
    def predict(self, X):
        """Make predictions using the trained tree."""
        return np.array([self._predict_single(x, self.tree) for x in X])
    
    def _build_tree(self, X, y, depth):
        """Recursively build the decision tree."""
        n_samples, n_features = X.shape
        
        # Base cases
        if depth >= self.max_depth or n_samples < self.min_samples_split or np.std(y) < 0.01:
            return {'type': 'leaf', 'value': np.mean(y)}
        
        # Find best split
        best_feature, best_threshold, best_gain = self._find_best_split(X, y)
        
        if best_gain <= 0:
            return {'type': 'leaf', 'value': np.mean(y)}
        
        # Update feature importance
        self.feature_importances_[best_feature] += best_gain * n_samples
        
        # Split data
        left_mask = X[:, best_feature] <= best_threshold
        right_mask = ~left_mask
        
        # Recursively build left and right subtrees
        left_tree = self._build_tree(X[left_mask], y[left_mask], depth + 1)
        right_tree = self._build_tree(X[right_mask], y[right_mask], depth + 1)
        
        return {
            'type': 'split',
            'feature': best_feature,
            'threshold': best_threshold,
            'left': left_tree,
            'right': right_tree
        }
    
    def _find_best_split(self, X, y):
        """Find the best feature and threshold to split on."""
        n_samples, n_features = X.shape
        best_gain = 0
        best_feature = 0
        best_threshold = 0
        
        current_variance = np.var(y)
        
        for feature in range(n_features):
            thresholds = np.unique(X[:, feature])
            
            for threshold in thresholds:
                left_mask = X[:, feature] <= threshold
                right_mask = ~left_mask
                
                if np.sum(left_mask) < 2 or np.sum(right_mask) < 2:
                    continue
                
                # Calculate weighted variance reduction
                left_var = np.var(y[left_mask])
                right_var = np.var(y[right_mask])
                
                n_left = np.sum(left_mask)
                n_right = np.sum(right_mask)
                
                weighted_var = (n_left * left_var + n_right * right_var) / n_samples
                gain = current_variance - weighted_var
                
                if gain > best_gain:
                    best_gain = gain
                    best_feature = feature
                    best_threshold = threshold
        
        return best_feature, best_threshold, best_gain
    
    def _predict_single(self, x, tree):
        """Make prediction for a single sample."""
        if tree['type'] == 'leaf':
            return tree['value']
        
        if x[tree['feature']] <= tree['threshold']:
            return self._predict_single(x, tree['left'])
        else:
            return self._predict_single(x, tree['right'])


class CustomRandomForestRegressor:
    """
    Custom Random Forest implementation from scratch.
    NO external ML libraries - built using our custom decision trees.
    """
    
    def __init__(self, n_estimators=10, max_depth=5, min_samples_split=5):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.trees = []
        self.feature_names = None
        self.feature_importances_ = None
    
    def fit(self, X, y, feature_names=None):
        """Train the random forest from scratch."""
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        self.trees = []
        
        n_samples, n_features = X.shape
        
        print(f"Training {self.n_estimators} custom decision trees from scratch...")
        
        for i in range(self.n_estimators):
            # Bootstrap sampling
            indices = np.random.choice(n_samples, n_samples, replace=True)
            X_bootstrap = X[indices]
            y_bootstrap = y[indices]
            
            # Train tree
            tree = SimpleDecisionTreeRegressor(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split
            )
            tree.fit(X_bootstrap, y_bootstrap, self.feature_names)
            self.trees.append(tree)
            
            if (i + 1) % 5 == 0:
                print(f"  Trained {i + 1}/{self.n_estimators} trees...")
        
        # Calculate average feature importances
        self.feature_importances_ = np.mean([tree.feature_importances_ for tree in self.trees], axis=0)
        
        return self
    
    def predict(self, X):
        """Make predictions using all trees (averaging)."""
        predictions = np.array([tree.predict(X) for tree in self.trees])
        return np.mean(predictions, axis=0)


def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load and validate the training dataset."""
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    
    df = pd.read_csv(dataset_path)
    
    required_cols = [
        'skill_overlap', 'required_skill_coverage', 'keyword_overlap',
        'experience_similarity', 'education_match', 'project_relevance',
        'match_score'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    print(f"✅ Loaded dataset: {len(df)} samples")
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Extract features and target variable."""
    feature_columns = [
        'skill_overlap', 'required_skill_coverage', 'keyword_overlap',
        'experience_similarity', 'education_match', 'project_relevance'
    ]
    
    X = df[feature_columns].values
    y = df['match_score'].values
    
    print(f"✅ Feature matrix: {X.shape}")
    print(f"   Target vector: {y.shape}")
    print(f"   Score range: {y.min():.1f} - {y.max():.1f}")
    
    return X, y, feature_columns


def train_test_split(X, y, test_size=0.2, random_state=42):
    """Simple train-test split implementation."""
    np.random.seed(random_state)
    n_samples = len(X)
    n_test = int(n_samples * test_size)
    
    indices = np.random.permutation(n_samples)
    test_indices = indices[:n_test]
    train_indices = indices[n_test:]
    
    return X[train_indices], X[test_indices], y[train_indices], y[test_indices]


def evaluate_model(y_true, y_pred):
    """Calculate evaluation metrics."""
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # R² score
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {'mae': mae, 'rmse': rmse, 'r2': r2}


def save_custom_model(model, metadata, model_path, metadata_path):
    """Save the custom model and metadata."""
    import pickle
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # Save model using pickle
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"✅ Custom model saved: {model_path}")
    
    # Save metadata
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Metadata saved: {metadata_path}")


def main():
    """Main training pipeline for custom ML model."""
    print("🚀 Custom ML Model Training (From Scratch)")
    print("=" * 70)
    print("   ✓ NO scikit-learn or pre-trained APIs used")
    print("   ✓ Custom RandomForest implementation")
    print("   ✓ Built entirely from scratch using Python/NumPy")
    print("=" * 70)
    
    # Paths
    dataset_path = os.path.join(BACKEND_ROOT, "ml", "dataset", "resume_job_matches.csv")
    model_path = os.path.join(BACKEND_ROOT, "ml", "artifacts", "custom_resume_job_match_model.pkl")
    metadata_path = os.path.join(BACKEND_ROOT, "ml", "artifacts", "custom_model_metadata.json")
    
    print(f"\n📁 Paths:")
    print(f"   Dataset:  {dataset_path}")
    print(f"   Model:    {model_path}")
    print(f"   Metadata: {metadata_path}\n")
    
    try:
        # Load data
        df = load_dataset(dataset_path)
        X, y, feature_names = prepare_features(df)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print(f"✅ Data split:")
        print(f"   Training: {len(X_train)} samples")
        print(f"   Testing:  {len(X_test)} samples\n")
        
        # Train custom model
        print("🔄 Training Custom Random Forest from SCRATCH...")
        model = CustomRandomForestRegressor(
            n_estimators=20,
            max_depth=6,
            min_samples_split=3
        )
        model.fit(X_train, y_train, feature_names)
        
        # Evaluate
        print(f"\n📊 Evaluating model...")
        y_pred = model.predict(X_test)
        metrics = evaluate_model(y_test, y_pred)
        
        print(f"✅ Model Performance:")
        print(f"   MAE:  {metrics['mae']:.2f}")
        print(f"   RMSE: {metrics['rmse']:.2f}")
        print(f"   R²:   {metrics['r2']:.3f}")
        
        # Create metadata
        metadata = {
            'model_type': 'CustomRandomForestRegressor',
            'custom_trained': True,
            'pre_trained_used': False,
            'from_scratch': True,
            'version': '1.0',
            'features': feature_names,
            'trained_at': datetime.now().isoformat(),
            'dataset_size': len(df),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'evaluation_metrics': {
                'mae': round(metrics['mae'], 3),
                'rmse': round(metrics['rmse'], 3),
                'r2': round(metrics['r2'], 3)
            },
            'hyperparameters': {
                'n_estimators': 20,
                'max_depth': 6,
                'min_samples_split': 3
            },
            'feature_importance': {
                name: round(importance, 3) 
                for name, importance in zip(feature_names, model.feature_importances_)
            },
            'notes': 'Custom ML model built entirely from scratch without any external ML libraries or pre-trained APIs'
        }
        
        # Save model
        save_custom_model(model, metadata, model_path, metadata_path)
        
        # Print feature importance
        print(f"\n📊 Feature Importance:")
        for name, importance in metadata['feature_importance'].items():
            print(f"   {name:25} {importance:.3f}")
        
        print("\n" + "=" * 70)
        print("🎉 Custom ML Model Training COMPLETED!")
        print("=" * 70)
        print(f"   ✓ Trained {model.n_estimators} decision trees from scratch")
        print(f"   ✓ NO external ML libraries used")
        print(f"   ✓ Model ready at: {model_path}")
        print(f"   ✓ Performance: MAE {metrics['mae']:.2f}, R² {metrics['r2']:.3f}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
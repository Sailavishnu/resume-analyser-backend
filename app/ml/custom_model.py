"""
Custom ML Model Implementation from Scratch (No external ML libraries).

Implements SimpleDecisionTreeRegressor and CustomRandomForestRegressor
from scratch using pure Python and NumPy.
"""
import numpy as np
from typing import List, Optional, Dict, Any


class SimpleDecisionTreeRegressor:
    """
    Custom Decision Tree Regressor implemented from scratch.
    NO external ML libraries used - pure Python/NumPy implementation.
    """
    
    def __init__(self, max_depth: int = 5, min_samples_split: int = 5):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.tree = None
        self.feature_names = None
        self.feature_importances_ = None
    
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None):
        """Train the decision tree from scratch."""
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        self.feature_importances_ = np.zeros(X.shape[1])
        self.tree = self._build_tree(X, y, depth=0)
        
        # Normalize feature importances
        if self.feature_importances_.sum() > 0:
            self.feature_importances_ = self.feature_importances_ / self.feature_importances_.sum()
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using the trained tree."""
        return np.array([self._predict_single(x, self.tree) for x in X])
    
    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> dict:
        """Recursively build the decision tree."""
        n_samples, n_features = X.shape
        
        # Base cases
        if depth >= self.max_depth or n_samples < self.min_samples_split or np.std(y) < 0.01:
            return {'type': 'leaf', 'value': float(np.mean(y))}
        
        # Find best split
        best_feature, best_threshold, best_gain = self._find_best_split(X, y)
        
        if best_gain <= 0:
            return {'type': 'leaf', 'value': float(np.mean(y))}
        
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
    
    def _find_best_split(self, X: np.ndarray, y: np.ndarray):
        """Find the best feature and threshold to split on."""
        n_samples, n_features = X.shape
        best_gain = 0.0
        best_feature = 0
        best_threshold = 0.0
        
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
    
    def _predict_single(self, x: np.ndarray, tree: dict) -> float:
        """Make prediction for a single sample."""
        if tree['type'] == 'leaf':
            return float(tree['value'])
        
        if x[tree['feature']] <= tree['threshold']:
            return self._predict_single(x, tree['left'])
        else:
            return self._predict_single(x, tree['right'])


class CustomRandomForestRegressor:
    """
    Custom Random Forest implementation from scratch.
    NO external ML libraries - built using our custom decision trees.
    """
    
    def __init__(self, n_estimators: int = 20, max_depth: int = 6, min_samples_split: int = 3):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.trees: List[SimpleDecisionTreeRegressor] = []
        self.feature_names = None
        self.feature_importances_ = None
    
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: Optional[List[str]] = None):
        """Train the random forest from scratch."""
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
        self.trees = []
        
        n_samples, n_features = X.shape
        
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
        
        # Calculate average feature importances
        if self.trees:
            self.feature_importances_ = np.mean([tree.feature_importances_ for tree in self.trees], axis=0)
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using all trees (averaging)."""
        if not self.trees:
            raise ValueError("Model is not fitted yet.")
        predictions = np.array([tree.predict(X) for tree in self.trees])
        return np.mean(predictions, axis=0)

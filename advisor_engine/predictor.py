import os
import pickle
from typing import Dict, Any, Optional
import pandas as pd

class SchemaPredictor:
    _models: Optional[Dict[str, Any]] = None

    @classmethod
    def _load_model(cls) -> None:
        """
        I use this to lazy-load my serialized model files from the disk only when needed.
        """
        if cls._models is not None:
            return
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "ml_artifacts", "model_pipeline.pkl")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Trained model artifacts not found at '{model_path}'. "
                "Please run 'python manage.py train_model' first."
            )
            
        try:
            with open(model_path, "rb") as f:
                cls._models = pickle.load(f)
        except Exception as e:
            raise IOError(f"Failed to load model file: {str(e)}")

    def predict_schema_needs(self, feature_dataframe: pd.DataFrame) -> Dict[str, str]:
        """
        I pass my feature DataFrame in here. This method fires up my classifiers,
        runs the predictions, and returns my recommendations as a dictionary.
        """
        # Make sure I've loaded my model checkpoints first
        self._load_model()
        
        if self._models is None:
            raise RuntimeError("Model classifiers dictionary was not loaded properly.")
            
        # Double check that the DataFrame has the exact columns I trained it on
        expected_cols = [
            "total_entities",
            "avg_attributes_per_entity",
            "has_unstructured_data",
            "nested_entities_count",
            "max_cardinality_score",
            "expected_read_write_ratio",
            "is_realtime_essential",
            "data_growth_rate_gb_month"
        ]
        
        # Order columns to match the classifier inputs
        for col in expected_cols:
            if col not in feature_dataframe.columns:
                raise ValueError(f"Missing expected feature column: {col}")
                
        input_data = feature_dataframe[expected_cols]
        
        recommendations: Dict[str, str] = {}
        for target, clf in self._models.items():
            pred_val = clf.predict(input_data)[0]
            recommendations[target] = str(pred_val)
            
        return recommendations

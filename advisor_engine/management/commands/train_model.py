import os
import pickle
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

class Command(BaseCommand):
    help = 'Generates synthetic dataset based on architectural rules, trains models and serializes them.'

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Initializing model training environment...")
        
        # 1. Reproducibility seed setup
        np.random.seed(42)
        n_samples = 3000
        
        # 2. Features generation
        total_entities = np.random.randint(1, 31, size=n_samples)
        avg_attributes = np.random.uniform(2.0, 25.0, size=n_samples)
        has_unstructured = np.random.choice([0, 1], size=n_samples, p=[0.6, 0.4])
        
        # nested count depends on unstructured data
        nested_entities = []
        for hu in has_unstructured:
            if hu == 1:
                nested_entities.append(np.random.randint(1, 12))
            else:
                nested_entities.append(0)
        nested_entities = np.array(nested_entities)
        
        max_cardinality = np.random.choice([0, 1, 2, 3], size=n_samples, p=[0.2, 0.1, 0.5, 0.2])
        rw_ratio = np.random.uniform(0.1, 35.0, size=n_samples)
        realtime = np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3])
        growth = np.random.uniform(0.1, 1000.0, size=n_samples)
        
        df = pd.DataFrame({
            "total_entities": total_entities,
            "avg_attributes_per_entity": avg_attributes,
            "has_unstructured_data": has_unstructured,
            "nested_entities_count": nested_entities,
            "max_cardinality_score": max_cardinality,
            "expected_read_write_ratio": rw_ratio,
            "is_realtime_essential": realtime,
            "data_growth_rate_gb_month": growth
        })
        
        # 3. Label targets using rules matrix
        def assign_labels(row: pd.Series) -> pd.Series:
            hu = row['has_unstructured_data']
            ne = row['nested_entities_count']
            mc = row['max_cardinality_score']
            rw = row['expected_read_write_ratio']
            rt = row['is_realtime_essential']
            gr = row['data_growth_rate_gb_month']
            te = row['total_entities']
            avg_a = row['avg_attributes_per_entity']
            
            # Defaults
            paradigm = "Relational"
            normalization = "3NF"
            indexing = "B-Tree_Heavy"
            scaling = "Vertical"
            
            # Rule A: Unstructured data + nested fields -> Document Store
            if hu == 1 and ne >= 2:
                paradigm = "Document"
                normalization = "Denormalized_Flat"
                indexing = "Composite_Heavy"
            # Rule B: Dense relations (M:N)
            elif mc == 3:
                if rt == 1 and gr > 50.0:
                    paradigm = "Graph"
                    normalization = "Denormalized_Flat"
                    indexing = "Covering_Index"
                else:
                    paradigm = "Relational"
                    normalization = "3NF"
                    indexing = "Composite_Heavy"
            else:
                # Key-value fallback
                if rw > 20.0 and te < 5 and hu == 0:
                    paradigm = "Key-Value"
                    normalization = "Denormalized_Flat"
                    indexing = "B-Tree_Heavy"
                    
            if paradigm in ("Document", "Key-Value"):
                normalization = "Denormalized_Flat"
                
            # Rule C: Read heavy workload
            if rw > 15.0:
                scaling = "Read_Replicas"
                indexing = "Covering_Index"
            else:
                # Default indexing rules
                if te > 12 or avg_a > 12.0:
                    indexing = "Composite_Heavy"
                else:
                    indexing = "B-Tree_Heavy"
                
                # Default scaling rules
                if gr > 100.0:
                    scaling = "Horizontal_Sharding"
                elif rw < 1.0: # Write heavy
                    scaling = "Horizontal_Sharding"
                    
            # Rule D: Extreme data growth overrides scaling
            if gr > 500.0:
                scaling = "Horizontal_Sharding"
                
            return pd.Series([paradigm, normalization, indexing, scaling])
            
        targets_df = df.apply(assign_labels, axis=1)
        targets_df.columns = ["recommended_db_paradigm", "normalization_target", "indexing_strategy", "scaling_strategy"]
        
        # Merge features and targets
        full_df = pd.concat([df, targets_df], axis=1)
        
        # 4. Data splitting
        features_cols = list(df.columns)
        targets_cols = list(targets_df.columns)
        
        X = full_df[features_cols]
        y = full_df[targets_cols]
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 5. Algorithm Choice: Multi-model training
        self.stdout.write(f"Training RandomForest models on {len(X_train)} samples...")
        models: Dict[str, RandomForestClassifier] = {}
        
        for col in targets_cols:
            self.stdout.write(f"Training classifier for target: '{col}'...")
            clf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)
            clf.fit(X_train, y_train[col])
            models[col] = clf
            
            # Predict and evaluate
            preds = clf.predict(X_val)
            self.stdout.write(self.style.SUCCESS(f"Evaluation report for target: {col}"))
            report = classification_report(y_val[col], preds, zero_division=0)
            self.stdout.write(report)
            
        # 6. File Serialization
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # advisor_engine
        artifacts_dir = os.path.join(base_dir, "ml_artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        
        model_path = os.path.join(artifacts_dir, "model_pipeline.pkl")
        try:
            with open(model_path, "wb") as f:
                pickle.dump(models, f)
            self.stdout.write(self.style.SUCCESS(f"Successfully serialized model pipeline to {model_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to serialize model pipeline: {str(e)}"))

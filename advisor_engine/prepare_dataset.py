import os
import json
import re
import glob
import hashlib
from typing import Dict, Any, List, Optional
import pandas as pd

def deterministic_hash(seed_str: str) -> float:
    """
    Generates a deterministic float between 0.0 and 1.0 based on seed string.
    Ensures reproducibility of random distributions.
    """
    h = hashlib.md5(seed_str.encode("utf-8")).hexdigest()
    val = int(h, 16)
    return (val % 10000) / 10000.0

def analyze_json_object(obj: Any) -> Dict[str, Any]:
    """
    Recursively analyzes a JSON object/dict to extract features.
    """
    total_attrs = 0
    nested_count = 0
    has_unstructured = 0
    
    def traverse(item: Any, current_depth: int) -> int:
        nonlocal total_attrs, nested_count, has_unstructured
        if current_depth > 1:
            nested_count += 1
        depth = current_depth
        if isinstance(item, dict):
            total_attrs += len(item)
            sub_depths = [traverse(v, current_depth + 1) for v in item.values()]
            if sub_depths:
                depth = max(sub_depths)
        elif isinstance(item, list):
            has_unstructured = 1
            sub_depths = [traverse(elem, current_depth + 1) for elem in item]
            if sub_depths:
                depth = max(sub_depths)
        return depth
        
    max_depth = traverse(obj, 1)
    return {
        "total_attrs": total_attrs,
        "nested_count": nested_count,
        "has_unstructured": has_unstructured,
        "max_depth": max_depth
    }

def process_mongodb_datasets(directory_path: str) -> List[Dict[str, Any]]:
    """
    Reads MongoDB sample collections, extracts features, and labels as Document.
    """
    records: List[Dict[str, Any]] = []
    if not os.path.exists(directory_path):
        print(f"Warning: MongoDB path '{directory_path}' not found.")
        return records

    search_path = os.path.join(directory_path, "*.json")
    files = glob.glob(search_path)
    print(f"Found {len(files)} MongoDB JSON files to process.")

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue
                # MongoDB exports can be either JSON arrays or raw objects
                data = json.loads(content)
                
                # If it's a list, analyze the first element to get the document structure
                rep_obj = data[0] if isinstance(data, list) and len(data) > 0 else data
                if not isinstance(rep_obj, dict):
                    continue
                
                analysis = analyze_json_object(rep_obj)
                
                # Determine features
                total_entities = 1
                avg_attributes_per_entity = float(analysis["total_attrs"])
                has_unstructured_data = 1 if analysis["has_unstructured"] or analysis["max_depth"] > 2 else 0
                nested_entities_count = analysis["nested_count"]
                max_cardinality_score = 1 if nested_entities_count > 0 else 0
                
                # Workload Simulation (Deterministic based on filename)
                h_val = deterministic_hash(filename)
                expected_read_write_ratio = 1.0 + h_val * 19.0 # 1.0 to 20.0
                is_realtime_essential = 1 if deterministic_hash(filename + "_rt") > 0.4 else 0
                data_growth_rate_gb_month = 5.0 + deterministic_hash(filename + "_growth") * 145.0 # 5 to 150 GB
                
                # Labels
                db_type = "document"
                normalization_form = "denormalized"
                sharding_key = "required" if data_growth_rate_gb_month > 30.0 else "not_required"
                indexing_strategy = "compound_index" if nested_entities_count > 2 else "single_field_index"
                
                records.append({
                    "total_entities": total_entities,
                    "avg_attributes_per_entity": avg_attributes_per_entity,
                    "has_unstructured_data": has_unstructured_data,
                    "nested_entities_count": nested_entities_count,
                    "max_cardinality_score": max_cardinality_score,
                    "expected_read_write_ratio": expected_read_write_ratio,
                    "is_realtime_essential": is_realtime_essential,
                    "data_growth_rate_gb_month": data_growth_rate_gb_month,
                    "db_type": db_type,
                    "normalization_form": normalization_form,
                    "indexing_strategy": indexing_strategy,
                    "sharding_key": sharding_key
                })
        except Exception as e:
            # Silently skip malformed/huge metadata exports or system.indexes files
            pass
            
    return records

def process_spider_dataset(tables_json_path: str) -> List[Dict[str, Any]]:
    """
    Parses tables.json from Spider dataset and labels as Relational.
    """
    records: List[Dict[str, Any]] = []
    if not os.path.exists(tables_json_path):
        print(f"Warning: Spider file '{tables_json_path}' not found.")
        return records
        
    try:
        with open(tables_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        print(f"Processing {len(data)} databases from Spider dataset.")
        for db in data:
            db_id = db.get("db_id", "")
            table_names = db.get("table_names", [])
            column_names = db.get("column_names", [])
            column_types = db.get("column_types", [])
            foreign_keys = db.get("foreign_keys", [])
            
            total_entities = len(table_names)
            if total_entities == 0:
                continue
                
            avg_attributes_per_entity = float(len(column_names)) / total_entities
            
            # Check for binary/unstructured keywords in types
            has_unstructured_data = 1 if any(t.lower() in ("blob", "json") for t in column_types) else 0
            
            nested_entities_count = 0
            
            # Map foreign key density to cardinality score
            if len(foreign_keys) == 0:
                max_cardinality_score = 0
            elif len(foreign_keys) >= total_entities:
                max_cardinality_score = 3 # Many-to-many join density
            else:
                max_cardinality_score = 2 # One-to-many primary
                
            # Workload simulation
            h_val = deterministic_hash(db_id)
            expected_read_write_ratio = 0.5 + h_val * 4.5 # 0.5 to 5.0
            is_realtime_essential = 1 if deterministic_hash(db_id + "_rt") > 0.75 else 0
            data_growth_rate_gb_month = 0.1 + deterministic_hash(db_id + "_growth") * 19.9 # 0.1 to 20 GB
            
            # Labels
            db_type = "relational"
            normalization_form = "3nf"
            sharding_key = "required" if data_growth_rate_gb_month > 50.0 else "not_required"
            indexing_strategy = "primary_key_index"
            
            records.append({
                "total_entities": total_entities,
                "avg_attributes_per_entity": avg_attributes_per_entity,
                "has_unstructured_data": has_unstructured_data,
                "nested_entities_count": nested_entities_count,
                "max_cardinality_score": max_cardinality_score,
                "expected_read_write_ratio": expected_read_write_ratio,
                "is_realtime_essential": is_realtime_essential,
                "data_growth_rate_gb_month": data_growth_rate_gb_month,
                "db_type": db_type,
                "normalization_form": normalization_form,
                "indexing_strategy": indexing_strategy,
                "sharding_key": sharding_key
            })
    except Exception as e:
        print(f"Error parsing Spider dataset: {str(e)}")
        
    return records

def process_sql_create_context(file_path: str, max_records: int = 2500) -> List[Dict[str, Any]]:
    """
    Parses a subset of SQL Create Context tables and labels as Relational.
    """
    records: List[Dict[str, Any]] = []
    if not os.path.exists(file_path):
        print(f"Warning: SQL Create Context file '{file_path}' not found.")
        return records
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        sliced_data = data[:max_records]
        print(f"Processing first {len(sliced_data)} schemas from SQL Create Context.")
        
        for idx, entry in enumerate(sliced_data):
            ddl = entry.get("context", "")
            
            # Regex to extract create tables
            tables = re.findall(r"CREATE\s+TABLE\s+(\w+)", ddl, re.IGNORECASE)
            total_entities = len(tables) if tables else 1
            
            # Parse column definitions to approximate column count
            columns = re.findall(r"(\w+)\s+(VARCHAR|INTEGER|TEXT|REAL|NUMERIC|BLOB|JSON|DATE|CHAR)", ddl, re.IGNORECASE)
            total_cols = len(columns) if columns else 3 # Default fallback
            
            avg_attributes_per_entity = float(total_cols) / total_entities
            
            # Unstructured check
            has_unstructured_data = 1 if any(c[1].upper() in ("BLOB", "JSON") for c in columns) else 0
            
            nested_entities_count = 0
            
            # Simple check for foreign key constraints
            has_fk = "FOREIGN KEY" in ddl.upper()
            max_cardinality_score = 2 if has_fk else 0
            
            # Workload simulation
            seed = f"ddl_{idx}"
            h_val = deterministic_hash(seed)
            expected_read_write_ratio = 0.5 + h_val * 4.5
            is_realtime_essential = 1 if deterministic_hash(seed + "_rt") > 0.8 else 0
            data_growth_rate_gb_month = 0.1 + deterministic_hash(seed + "_growth") * 14.9 # 0.1 to 15 GB
            
            # Labels
            db_type = "relational"
            normalization_form = "3nf"
            sharding_key = "not_required"
            indexing_strategy = "primary_key_index"
            
            records.append({
                "total_entities": total_entities,
                "avg_attributes_per_entity": avg_attributes_per_entity,
                "has_unstructured_data": has_unstructured_data,
                "nested_entities_count": nested_entities_count,
                "max_cardinality_score": max_cardinality_score,
                "expected_read_write_ratio": expected_read_write_ratio,
                "is_realtime_essential": is_realtime_essential,
                "data_growth_rate_gb_month": data_growth_rate_gb_month,
                "db_type": db_type,
                "normalization_form": normalization_form,
                "indexing_strategy": indexing_strategy,
                "sharding_key": sharding_key
            })
    except Exception as e:
        print(f"Error parsing SQL Create Context: {str(e)}")
        
    return records

def compile_dataset() -> None:
    """
    Gathers records from all datasets, merges them, and saves to ml_artifacts.
    """
    print("Starting dataset preparation...")
    
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # schema_advisor_root
    mongodb_dir = os.path.join(base_dir, "dataset", "json_dataset_mongodb")
    spider_path = os.path.join(base_dir, "dataset", "spider", "tables.json")
    sql_ctx_path = os.path.join(base_dir, "dataset", "sql_create_context_v4.json")
    output_path = os.path.join(base_dir, "advisor_engine", "ml_artifacts", "training_dataset.csv")
    
    # Ingest
    mongodb_records = process_mongodb_datasets(mongodb_dir)
    spider_records = process_spider_dataset(spider_path)
    sql_ctx_records = process_sql_create_context(sql_ctx_path, max_records=2500)
    
    all_records = mongodb_records + spider_records + sql_ctx_records
    print(f"Total compiled records: {len(all_records)}")
    
    if not all_records:
        print("Error: No records generated. Aborting CSV write.")
        return
        
    # Compile
    df = pd.DataFrame(all_records)
    
    # Ensure columns order
    columns = [
        "total_entities",
        "avg_attributes_per_entity",
        "has_unstructured_data",
        "nested_entities_count",
        "max_cardinality_score",
        "expected_read_write_ratio",
        "is_realtime_essential",
        "data_growth_rate_gb_month",
        "db_type",
        "normalization_form",
        "indexing_strategy",
        "sharding_key"
    ]
    
    df = df[columns]
    
    # Ensure target directories exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Successfully generated training dataset at '{output_path}'. Shape: {df.shape}")

if __name__ == "__main__":
    compile_dataset()

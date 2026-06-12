import pandas as pd
from typing import Dict, Any, List

def extract_features(data: Dict[str, Any]) -> pd.DataFrame:
    """
    I use this function to pull out exactly 8 features from the parsed schema.
    It builds a single-row Pandas DataFrame to feed into my ML predictor.
    """
    entities: List[Dict[str, Any]] = data.get("entities", [])
    relationships: List[Dict[str, Any]] = data.get("relationships", [])
    requirements: Dict[str, Any] = data.get("requirements", {})
    
    # Feature 1: count how many entities I have
    total_entities: int = len(entities)
    
    # Feature 2: compute average attribute density
    total_attributes: int = 0
    for entity in entities:
        total_attributes += len(entity.get("attributes", []))
    avg_attributes_per_entity: float = (
        float(total_attributes) / total_entities if total_entities > 0 else 0.0
    )
    
    # Feature 3: flag if I have unstructured data types
    unstructured_keywords = {"json", "blob", "text", "variant", "array", "dict"}
    has_unstructured_data: int = 0
    for entity in entities:
        for attr in entity.get("attributes", []):
            data_type = str(attr.get("data_type", "")).lower().replace(" ", "")
            # Check if any keyword matches
            if any(kw in data_type for kw in unstructured_keywords):
                has_unstructured_data = 1
                break
        if has_unstructured_data == 1:
            break
            
    # Feature 4: count my nested schemas
    nested_entities_count: int = 0
    for entity in entities:
        is_nested = entity.get("is_nested", False)
        if isinstance(is_nested, str):
            is_nested = is_nested.lower() in ("true", "1", "yes")
        if is_nested:
            nested_entities_count += 1
            
    # Feature 5: convert relationship cardinality to a numeric score
    cardinality_map = {
        "N:M": 3, "M:N": 3, "MANY:MANY": 3,
        "1:N": 2, "N:1": 2, "ONE:MANY": 2, "MANY:ONE": 2,
        "1:1": 1, "ONE:ONE": 1
    }
    max_cardinality_score: int = 0
    for rel in relationships:
        card = str(rel.get("cardinality", "")).upper().replace(" ", "")
        score = cardinality_map.get(card, 0)
        if score > max_cardinality_score:
            max_cardinality_score = score
            
    # Feature 6: extract read/write ratio requirement
    expected_read_write_ratio: float = float(requirements.get("read_write_ratio", 1.0))
    
    # Feature 7: check if I absolutely need realtime latency
    realtime = requirements.get("is_realtime_essential", False)
    if isinstance(realtime, str):
        realtime = realtime.lower() in ("true", "1", "yes")
    is_realtime_essential: int = 1 if realtime else 0
    
    # Feature 8: monthly data growth estimate in GB
    data_growth_rate_gb_month: float = float(requirements.get("data_growth_rate_gb_month", 0.0))
    
    # Package everything up in a DataFrame
    features_dict = {
        "total_entities": total_entities,
        "avg_attributes_per_entity": avg_attributes_per_entity,
        "has_unstructured_data": has_unstructured_data,
        "nested_entities_count": nested_entities_count,
        "max_cardinality_score": max_cardinality_score,
        "expected_read_write_ratio": expected_read_write_ratio,
        "is_realtime_essential": is_realtime_essential,
        "data_growth_rate_gb_month": data_growth_rate_gb_month
    }
    
    # Maintain my precise column ordering
    columns = [
        "total_entities",
        "avg_attributes_per_entity",
        "has_unstructured_data",
        "nested_entities_count",
        "max_cardinality_score",
        "expected_read_write_ratio",
        "is_realtime_essential",
        "data_growth_rate_gb_month"
    ]
    
    return pd.DataFrame([features_dict], columns=columns)

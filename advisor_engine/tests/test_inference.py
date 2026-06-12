import json
from typing import Dict, Any
import pandas as pd
from advisor_engine.parsers import parse_json
from advisor_engine.extractors import extract_features
from advisor_engine.predictor import SchemaPredictor
from advisor_engine.generators import BoilerplateGenerator

def test_predictor_relational_inference(mock_json_payload: str) -> None:
    """
    I am testing that SchemaPredictor correctly predicts 'Relational'
    for standard schema profiles.
    """
    parsed_data: Dict[str, Any] = parse_json(mock_json_payload)
    feature_df: pd.DataFrame = extract_features(parsed_data)

    predictor = SchemaPredictor()
    predictions: Dict[str, str] = predictor.predict_schema_needs(feature_df)

    # Verify that the output dict has all my target recommendation keys
    assert "recommended_db_paradigm" in predictions
    assert "normalization_target" in predictions
    assert "indexing_strategy" in predictions
    assert "scaling_strategy" in predictions

    # Verify that the predicted paradigm is Relational
    assert predictions["recommended_db_paradigm"] == "Relational"


def test_predictor_document_inference(mock_nosql_json_payload: str) -> None:
    """
    I am testing that SchemaPredictor recommends 'Document' store when given NoSQL-type structures.
    """
    parsed_data: Dict[str, Any] = parse_json(mock_nosql_json_payload)
    feature_df: pd.DataFrame = extract_features(parsed_data)

    predictor = SchemaPredictor()
    predictions: Dict[str, str] = predictor.predict_schema_needs(feature_df)

    assert "recommended_db_paradigm" in predictions
    assert predictions["recommended_db_paradigm"] == "Document"


def test_boilerplate_generator_sql(mock_json_payload: str) -> None:
    """
    I want to verify that BoilerplateGenerator produces correct SQL CREATE TABLE and FOREIGN KEY blocks.
    """
    parsed_data: Dict[str, Any] = parse_json(mock_json_payload)
    generator = BoilerplateGenerator(parsed_data, "Relational")
    sql_output: str = generator.generate()

    assert "CREATE TABLE User" in sql_output
    assert "CREATE TABLE Post" in sql_output
    assert "FOREIGN KEY" in sql_output
    assert "user_id INT" in sql_output or "user_id" in sql_output.lower()


def test_boilerplate_generator_nosql(mock_nosql_json_payload: str) -> None:
    """
    I want to verify that BoilerplateGenerator outputs the correct MongoDB $jsonSchema structure.
    """
    parsed_data: Dict[str, Any] = parse_json(mock_nosql_json_payload)
    generator = BoilerplateGenerator(parsed_data, "Document")
    nosql_output: str = generator.generate()

    # Try parsing the output to make sure it's valid JSON
    schema_dict: Dict[str, Any] = json.loads(nosql_output)

    # Verify that the top-level entity collections are set up correctly
    # Orders is the root collection here since Order is not nested
    assert "orders" in schema_dict
    assert "items" not in schema_dict  # items should not be at the root because Item is nested
    
    order_schema = schema_dict["orders"]
    assert "$jsonSchema" in order_schema
    assert order_schema["$jsonSchema"]["bsonType"] == "object"
    
    properties = order_schema["$jsonSchema"]["properties"]
    assert "metadata" in properties
    assert properties["metadata"]["bsonType"] == "string" or properties["metadata"]["bsonType"] == "object"
    
    # Double check that the nested entities are embedded correctly under the parent properties
    assert "items" in properties
    assert properties["items"]["bsonType"] == "array"
    assert "properties" in properties["items"]["items"]
    
    assert "delivery" in properties
    assert properties["delivery"]["bsonType"] == "object"

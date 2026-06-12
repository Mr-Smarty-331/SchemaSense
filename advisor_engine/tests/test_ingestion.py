import pytest
import pandas as pd
from typing import Dict, Any
from rest_framework.exceptions import ValidationError
from advisor_engine.parsers import parse_json, parse_xml
from advisor_engine.extractors import extract_features

def test_json_and_xml_parsers_match(mock_json_payload: str, mock_xml_payload: str) -> None:
    """
    I want to make sure my JSON and XML parsers produce the exact same python dicts
    for structurally identical payload schemas.
    """
    parsed_json: Dict[str, Any] = parse_json(mock_json_payload)
    parsed_xml: Dict[str, Any] = parse_xml(mock_xml_payload)

    # Check that all primary keys are here
    assert "entities" in parsed_json
    assert "relationships" in parsed_json
    assert "requirements" in parsed_json

    assert len(parsed_json["entities"]) == len(parsed_xml["entities"])
    assert len(parsed_json["relationships"]) == len(parsed_xml["relationships"])

    # Ensure my entities match after normalization runs
    for ej, ex in zip(parsed_json["entities"], parsed_xml["entities"]):
        assert ej["name"] == ex["name"]
        assert ej["is_nested"] == ex["is_nested"]
        assert len(ej["attributes"]) == len(ex["attributes"])
        for aj, ax in zip(ej["attributes"], ex["attributes"]):
            assert aj["name"] == ax["name"]
            assert aj["is_primary_key"] == ax["is_primary_key"]
            assert aj["is_nullable"] == ax["is_nullable"]

    # Make sure relationships parsed identically
    for rj, rx in zip(parsed_json["relationships"], parsed_xml["relationships"]):
        assert rj["from_entity"] == rx["from_entity"]
        assert rj["to_entity"] == rx["to_entity"]
        assert rj["cardinality"] == rx["cardinality"]

    # Make sure hardware/scaling requirements match
    assert float(parsed_json["requirements"]["read_write_ratio"]) == float(parsed_xml["requirements"]["read_write_ratio"])
    assert bool(parsed_json["requirements"]["is_realtime_essential"]) == bool(parsed_xml["requirements"]["is_realtime_essential"])
    assert float(parsed_json["requirements"]["data_growth_rate_gb_month"]) == float(parsed_xml["requirements"]["data_growth_rate_gb_month"])


def test_json_parser_errors(malformed_json_payload: str) -> None:
    """
    I am testing that my JSON parser raises validation errors when given broken syntax or wrong types.
    """
    with pytest.raises(ValidationError) as excinfo:
        parse_json(malformed_json_payload)
    assert "Invalid JSON string syntax" in str(excinfo.value)

    # Passing a non-string type should trigger my ValidationError
    with pytest.raises(ValidationError) as excinfo_type:
        parse_json(12345)  # type: ignore
    assert "Input must be a raw string" in str(excinfo_type.value)

    # An invalid root element like a list should also trigger an error
    with pytest.raises(ValidationError) as excinfo_root:
        parse_json("[1, 2, 3]")
    assert "JSON root must be an object" in str(excinfo_root.value)


def test_xml_parser_errors(malformed_xml_payload: str) -> None:
    """
    I'm testing my XML parser to verify it throws validation errors for broken XML.
    """
    with pytest.raises(ValidationError) as excinfo:
        parse_xml(malformed_xml_payload)
    assert "Error parsing XML securely" in str(excinfo.value)

    # Passing a non-string type should trigger ValidationError
    with pytest.raises(ValidationError) as excinfo_type:
        parse_xml(None)  # type: ignore
    assert "Input must be a raw string" in str(excinfo_type.value)


def test_xml_xxe_protection() -> None:
    """
    I need to make sure my XML parser blocks external entity injection (XXE) hacks.
    """
    xxe_payload = """<?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE test [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <Schema>
        <Entities>
            <Entity name="&xxe;">
                <Attribute name="id" data_type="integer"/>
            </Entity>
        </Entities>
    </Schema>
    """
    with pytest.raises(ValidationError) as excinfo:
        parse_xml(xxe_payload)
    assert "Error parsing XML securely" in str(excinfo.value)


def test_feature_extractor_dataframe_properties(mock_json_payload: str) -> None:
    """
    I'm testing my feature extractor here. I expect it to output a 1x8 Pandas DataFrame
    with the features set to the correct values.
    """
    parsed_data: Dict[str, Any] = parse_json(mock_json_payload)
    feature_df: pd.DataFrame = extract_features(parsed_data)

    # Confirm the output shape is 1x8
    assert feature_df.shape == (1, 8)

    # Confirm all my 8 columns are exactly correct
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
    assert list(feature_df.columns) == expected_cols

    # Verify the actual feature values matches my schema
    assert feature_df.loc[0, "total_entities"] == 2
    assert feature_df.loc[0, "avg_attributes_per_entity"] == 3.0
    assert feature_df.loc[0, "has_unstructured_data"] == 0
    assert feature_df.loc[0, "nested_entities_count"] == 0
    assert feature_df.loc[0, "max_cardinality_score"] == 2  # 1:N gets score 2
    assert feature_df.loc[0, "expected_read_write_ratio"] == 5.5
    assert feature_df.loc[0, "is_realtime_essential"] == 0
    assert feature_df.loc[0, "data_growth_rate_gb_month"] == 1.2

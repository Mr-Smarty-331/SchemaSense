import json
from json import JSONDecodeError
from typing import Dict, Any, List
from rest_framework.exceptions import ValidationError
import defusedxml.ElementTree as ET

def normalize_parsed_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    I wrote this helper to make sure all my entity attributes have 'is_primary_key' and 'is_nullable' flags.
    If they are missing, I default them based on basic conventions.
    Also, normalize requirements fields.
    """
    entities = data.get("entities", [])
    for entity in entities:
        attributes = entity.get("attributes", [])
        for attr in attributes:
            # Map type to data_type if only type is specified
            if "data_type" not in attr and "type" in attr:
                attr["data_type"] = attr["type"]

            # Figure out if it's the primary key
            if "is_primary_key" not in attr:
                attr_name = str(attr.get("name", "")).lower()
                attr["is_primary_key"] = attr_name == "id"
            else:
                val = attr["is_primary_key"]
                if isinstance(val, str):
                    attr["is_primary_key"] = val.lower() in ("true", "1", "yes")

            # Set defaults for nullability
            if "is_nullable" not in attr:
                attr["is_nullable"] = not attr["is_primary_key"]
            else:
                val = attr["is_nullable"]
                if isinstance(val, str):
                    attr["is_nullable"] = val.lower() not in ("false", "0", "no")

    # Normalize requirements keys (expected_read_write_ratio vs read_write_ratio)
    requirements = data.get("requirements", {})
    if "expected_read_write_ratio" in requirements and "read_write_ratio" not in requirements:
        requirements["read_write_ratio"] = requirements["expected_read_write_ratio"]
    elif "read_write_ratio" in requirements and "expected_read_write_ratio" not in requirements:
        requirements["expected_read_write_ratio"] = requirements["read_write_ratio"]

    return data

def parse_json(raw_json: str) -> Dict[str, Any]:
    """
    This is my JSON parser helper. It takes a raw JSON string, checks it, and returns a nice python dict.
    If things go south, I raise a DRF ValidationError so my view can catch it cleanly.
    """
    if not isinstance(raw_json, str):
        raise ValidationError("Input must be a raw string.")
    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            raise ValidationError("JSON root must be an object.")
        return normalize_parsed_data(data)
    except JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON string syntax: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Error parsing JSON: {str(e)}")

def parse_xml(raw_xml: str) -> Dict[str, Any]:
    """
    Here is my XML parser. I'm using defusedxml to keep it safe from external entity exploits.
    I traverse through the XML tree to pull out my entities, relationships, and requirements.
    """
    if not isinstance(raw_xml, str):
        raise ValidationError("Input must be a raw string.")
    try:
        root = ET.fromstring(raw_xml)
        
        entities: List[Dict[str, Any]] = []
        for entity_elem in root.findall(".//Entity"):
            name: str = entity_elem.get("name", "")
            is_nested_str: str = entity_elem.get("is_nested", "false").lower()
            is_nested: bool = is_nested_str in ("true", "1", "yes")
            
            attributes: List[Dict[str, Any]] = []
            for attr_elem in entity_elem.findall("Attribute"):
                attr_name: str = attr_elem.get("name", "")
                data_type: str = attr_elem.get("data_type", "")
                
                is_pk_raw = attr_elem.get("is_primary_key")
                is_null_raw = attr_elem.get("is_nullable")
                
                attr_dict: Dict[str, Any] = {
                    "name": attr_name,
                    "data_type": data_type
                }
                if is_pk_raw is not None:
                    attr_dict["is_primary_key"] = is_pk_raw.lower() in ("true", "1", "yes")
                if is_null_raw is not None:
                    attr_dict["is_nullable"] = is_null_raw.lower() not in ("false", "0", "no")
                    
                attributes.append(attr_dict)
                
            entities.append({
                "name": name,
                "is_nested": is_nested,
                "attributes": attributes
            })
            
        relationships: List[Dict[str, Any]] = []
        for rel_elem in root.findall(".//Relationship"):
            from_entity: str = rel_elem.get("from", "")
            to_entity: str = rel_elem.get("to", "")
            cardinality: str = rel_elem.get("cardinality", "1:1")
            relationships.append({
                "from_entity": from_entity,
                "to_entity": to_entity,
                "cardinality": cardinality
            })
            
        # Now let's extract the hardware/performance requirements
        req_elem = root.find(".//Requirements")
        read_write_ratio: float = 1.0
        is_realtime_essential: bool = False
        data_growth_rate_gb_month: float = 0.0
        
        if req_elem is not None:
            rw_ratio_str = req_elem.get("read_write_ratio")
            if rw_ratio_str is not None:
                read_write_ratio = float(rw_ratio_str)
                
            realtime_str = req_elem.get("realtime", "false").lower()
            is_realtime_essential = realtime_str in ("true", "1", "yes")
            
            growth_str = req_elem.get("growth_rate")
            if growth_str is not None:
                data_growth_rate_gb_month = float(growth_str)
                
        requirements: Dict[str, Any] = {
            "read_write_ratio": read_write_ratio,
            "is_realtime_essential": is_realtime_essential,
            "data_growth_rate_gb_month": data_growth_rate_gb_month
        }
        
        normalized_result = {
            "entities": entities,
            "relationships": relationships,
            "requirements": requirements
        }
        return normalize_parsed_data(normalized_result)
    except Exception as e:
        raise ValidationError(f"Error parsing XML securely: {str(e)}")

import pytest
from typing import Dict, Any

@pytest.fixture
def mock_json_payload() -> str:
    """
    Here is my fixture for a valid relational JSON schema payload.
    """
    return """
    {
        "entities": [
            {
                "name": "User",
                "is_nested": false,
                "attributes": [
                    {"name": "id", "data_type": "integer", "is_primary_key": true, "is_nullable": false},
                    {"name": "username", "data_type": "string", "is_primary_key": false, "is_nullable": false},
                    {"name": "email", "data_type": "string", "is_primary_key": false, "is_nullable": true}
                ]
            },
            {
                "name": "Post",
                "is_nested": false,
                "attributes": [
                    {"name": "id", "data_type": "integer", "is_primary_key": true, "is_nullable": false},
                    {"name": "title", "data_type": "string", "is_primary_key": false, "is_nullable": false},
                    {"name": "body", "data_type": "string", "is_primary_key": false, "is_nullable": true}
                ]
            }
        ],
        "relationships": [
            {
                "from_entity": "User",
                "to_entity": "Post",
                "cardinality": "1:N"
            }
        ],
        "requirements": {
            "read_write_ratio": 5.5,
            "is_realtime_essential": false,
            "data_growth_rate_gb_month": 1.2
        }
    }
    """

@pytest.fixture
def mock_nosql_json_payload() -> str:
    """
    This is my JSON schema fixture that triggers NoSQL Document paradigm predictions.
    It has unstructured fields and multiple nested entities.
    """
    return """
    {
        "entities": [
            {
                "name": "Order",
                "is_nested": false,
                "attributes": [
                    {"name": "id", "data_type": "integer", "is_primary_key": true, "is_nullable": false},
                    {"name": "metadata", "data_type": "json", "is_primary_key": false, "is_nullable": true},
                    {"name": "order_date", "data_type": "datetime", "is_primary_key": false, "is_nullable": false}
                ]
            },
            {
                "name": "Item",
                "is_nested": true,
                "attributes": [
                    {"name": "product_name", "data_type": "string", "is_primary_key": false, "is_nullable": false},
                    {"name": "price", "data_type": "number", "is_primary_key": false, "is_nullable": false}
                ]
            },
            {
                "name": "Delivery",
                "is_nested": true,
                "attributes": [
                    {"name": "tracking_num", "data_type": "string", "is_primary_key": false, "is_nullable": true},
                    {"name": "status", "data_type": "string", "is_primary_key": false, "is_nullable": false}
                ]
            }
        ],
        "relationships": [
            {
                "from_entity": "Order",
                "to_entity": "Item",
                "cardinality": "1:N"
            },
            {
                "from_entity": "Order",
                "to_entity": "Delivery",
                "cardinality": "1:1"
            }
        ],
        "requirements": {
            "read_write_ratio": 3.0,
            "is_realtime_essential": false,
            "data_growth_rate_gb_month": 12.5
        }
    }
    """

@pytest.fixture
def mock_xml_payload() -> str:
    """
    My fixture for a standard relational XML schema configuration.
    """
    return """<Schema>
    <Entities>
        <Entity name="User" is_nested="false">
            <Attribute name="id" data_type="integer" is_primary_key="true" is_nullable="false"/>
            <Attribute name="username" data_type="string" is_primary_key="false" is_nullable="false"/>
            <Attribute name="email" data_type="string" is_primary_key="false" is_nullable="true"/>
        </Entity>
        <Entity name="Post" is_nested="false">
            <Attribute name="id" data_type="integer" is_primary_key="true" is_nullable="false"/>
            <Attribute name="title" data_type="string" is_primary_key="false" is_nullable="false"/>
            <Attribute name="body" data_type="string" is_primary_key="false" is_nullable="true"/>
        </Entity>
    </Entities>
    <Relationships>
        <Relationship from="User" to="Post" cardinality="1:N"/>
    </Relationships>
    <Requirements read_write_ratio="5.5" realtime="false" growth_rate="1.2"/>
</Schema>
"""

@pytest.fixture
def mock_nosql_xml_payload() -> str:
    """
    This is my XML schema fixture that triggers a NoSQL Document recommendation.
    """
    return """<Schema>
    <Entities>
        <Entity name="Order" is_nested="false">
            <Attribute name="id" data_type="integer" is_primary_key="true" is_nullable="false"/>
            <Attribute name="metadata" data_type="json" is_primary_key="false" is_nullable="true"/>
            <Attribute name="order_date" data_type="datetime" is_primary_key="false" is_nullable="false"/>
        </Entity>
        <Entity name="Item" is_nested="true">
            <Attribute name="product_name" data_type="string" is_primary_key="false" is_nullable="false"/>
            <Attribute name="price" data_type="number" is_primary_key="false" is_nullable="false"/>
        </Entity>
        <Entity name="Delivery" is_nested="true">
            <Attribute name="tracking_num" data_type="string" is_primary_key="false" is_nullable="true"/>
            <Attribute name="status" data_type="string" is_primary_key="false" is_nullable="false"/>
        </Entity>
    </Entities>
    <Relationships>
        <Relationship from="Order" to="Item" cardinality="1:N"/>
        <Relationship from="Order" to="Delivery" cardinality="1:1"/>
    </Relationships>
    <Requirements read_write_ratio="3.0" realtime="false" growth_rate="12.5"/>
</Schema>
"""

@pytest.fixture
def malformed_json_payload() -> str:
    """
    A fixture that returns a broken JSON string to verify my error interceptors.
    """
    return "{ \"entities\": [ { \"name\": \"User\" "

@pytest.fixture
def malformed_xml_payload() -> str:
    """
    A fixture returning broken XML syntax to test my parse failure catch blocks.
    """
    return "<Schema><Entities><Entity name=\"User\"></Entities>"

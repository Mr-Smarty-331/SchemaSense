import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schema_advisor_core.settings')
django.setup()

from rest_framework.test import APIClient

def verify() -> None:
    client = APIClient()

    mock_json_payload = """
    {
        "entities": [
            {
                "name": "User",
                "is_nested": false,
                "attributes": [
                    {"name": "id", "data_type": "integer"},
                    {"name": "profile", "data_type": "json"}
                ]
            },
            {
                "name": "Post",
                "is_nested": true,
                "attributes": [
                    {"name": "id", "data_type": "integer"},
                    {"name": "content", "data_type": "text"}
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
            "read_write_ratio": 20.0,
            "is_realtime_essential": true,
            "data_growth_rate_gb_month": 2.5
        }
    }
    """

    print("--- 1. Sending valid JSON schema request to /api/v1/analyze/ ---")
    response = client.post('/api/v1/analyze/', {
        "payload_type": "JSON",
        "raw_payload": mock_json_payload
    }, format='json')

    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.data, indent=2)}")

    # Test NoSQL Document Store Trigger (Unstructured + Nesting count >= 2)
    mock_nosql_payload = """
    {
        "entities": [
            {
                "name": "Order",
                "is_nested": false,
                "attributes": [
                    {"name": "id", "data_type": "integer"},
                    {"name": "metadata", "data_type": "json"},
                    {"name": "order_date", "data_type": "datetime"}
                ]
            },
            {
                "name": "Item",
                "is_nested": true,
                "attributes": [
                    {"name": "product_name", "data_type": "string"},
                    {"name": "price", "data_type": "number"}
                ]
            },
            {
                "name": "Delivery",
                "is_nested": true,
                "attributes": [
                    {"name": "tracking_num", "data_type": "string"},
                    {"name": "status", "data_type": "string"}
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
            "read_write_ratio": 5.0,
            "is_realtime_essential": false,
            "data_growth_rate_gb_month": 150.0
        }
    }
    """

    print("\n--- 1b. Sending valid JSON schema request to trigger NoSQL Document paradigm ---")
    response_nosql = client.post('/api/v1/analyze/', {
        "payload_type": "JSON",
        "raw_payload": mock_nosql_payload
    }, format='json')

    print(f"Status Code: {response_nosql.status_code}")
    print(f"Response:\n{json.dumps(response_nosql.data, indent=2)}")

    print("\n--- 2. Sending invalid JSON to test error handling ---")
    response_error = client.post('/api/v1/analyze/', {
        "payload_type": "JSON",
        "raw_payload": "{ broken json: }"
    }, format='json')
    print(f"Status Code: {response_error.status_code}")
    print(f"Response:\n{json.dumps(response_error.data, indent=2)}")

    # Test GET /api/v1/recommendations/
    print("\n--- 3. Fetching recommendations from /api/v1/recommendations/ ---")
    get_response = client.get('/api/v1/recommendations/')
    print(f"Status Code: {get_response.status_code}")
    print(f"Response (Total requests in log): {len(get_response.data)}")
    if len(get_response.data) > 0:
        print(f"Nested logs structure:\n{json.dumps(get_response.data[0], indent=2)}")

if __name__ == "__main__":
    verify()

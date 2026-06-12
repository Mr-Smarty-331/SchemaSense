import pytest
from typing import Dict, Any, List
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from advisor_engine.models import AnalysisRequest, SchemaRecommendation

@pytest.mark.django_db
def test_analyze_valid_json_pipeline(mock_json_payload: str) -> None:
    """
    I am testing the E2E analysis pipeline with a valid JSON payload. Here I verify the 201 response, database record creation, and boilerplate output.
    """
    client = APIClient()
    url: str = reverse('analyze')
    
    # Double check the database is empty before running the test
    assert AnalysisRequest.objects.count() == 0
    assert SchemaRecommendation.objects.count() == 0

    response = client.post(url, {
        "payload_type": "JSON",
        "raw_payload": mock_json_payload
    }, format='json')

    # Check the status and output structure of the API response
    assert response.status_code == status.HTTP_201_CREATED
    data: Dict[str, Any] = response.data
    assert data["status"] == "success"
    assert "request_id" in data
    assert "recommendation" in data

    recomm: Dict[str, Any] = data["recommendation"]
    assert recomm["predicted_paradigm"] == "Relational"
    assert "generated_boilerplate" in recomm
    assert "CREATE TABLE User" in recomm["generated_boilerplate"]

    # Make sure the audit and recommendation rows were created in my DB
    assert AnalysisRequest.objects.count() == 1
    assert SchemaRecommendation.objects.count() == 1

    db_req = AnalysisRequest.objects.first()
    assert db_req is not None
    assert db_req.payload_type == "JSON"
    assert db_req.raw_payload == mock_json_payload.strip()

    db_recomm = SchemaRecommendation.objects.first()
    assert db_recomm is not None
    assert db_recomm.request == db_req
    assert db_recomm.predicted_paradigm == "Relational"


@pytest.mark.django_db
def test_analyze_valid_xml_pipeline(mock_xml_payload: str) -> None:
    """
    I am testing the E2E analysis pipeline with a valid XML payload.
    """
    client = APIClient()
    url: str = reverse('analyze')

    response = client.post(url, {
        "payload_type": "XML",
        "raw_payload": mock_xml_payload
    }, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    data: Dict[str, Any] = response.data
    assert data["status"] == "success"
    assert data["recommendation"]["predicted_paradigm"] == "Relational"
    assert "CREATE TABLE User" in data["recommendation"]["generated_boilerplate"]

    assert AnalysisRequest.objects.count() == 1
    assert SchemaRecommendation.objects.count() == 1


@pytest.mark.django_db
def test_analyze_invalid_payload_error(malformed_json_payload: str) -> None:
    """
    I want to verify that my pipeline returns a 400 Bad Request if the JSON payload is malformed.
    """
    client = APIClient()
    url: str = reverse('analyze')

    response = client.post(url, {
        "payload_type": "JSON",
        "raw_payload": malformed_json_payload
    }, format='json')

    # Verify I get a 400 response code
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data: Dict[str, Any] = response.data
    assert "error" in data
    assert data["error"] == "Parsing failed"
    assert "details" in data

    # Verify that nothing was written to my database logs
    assert AnalysisRequest.objects.count() == 0
    assert SchemaRecommendation.objects.count() == 0


@pytest.mark.django_db
def test_get_recommendations_history(mock_json_payload: str, mock_nosql_json_payload: str) -> None:
    """
    I am testing the GET history list endpoint to ensure I get back all past analysis requests.
    """
    client = APIClient()
    analyze_url: str = reverse('analyze')
    list_url: str = reverse('recommendations')

    # Fire off my first test request (predicts Relational)
    res1 = client.post(analyze_url, {
        "payload_type": "JSON",
        "raw_payload": mock_json_payload
    }, format='json')
    assert res1.status_code == status.HTTP_201_CREATED

    # Fire off my second test request (predicts Document)
    res2 = client.post(analyze_url, {
        "payload_type": "JSON",
        "raw_payload": mock_nosql_json_payload
    }, format='json')
    assert res2.status_code == status.HTTP_201_CREATED

    # Fetch and verify my history logs list
    response = client.get(list_url)
    assert response.status_code == status.HTTP_200_OK
    
    logs: List[Dict[str, Any]] = response.data
    # I expect 2 log entries ordered with the most recent first
    assert len(logs) == 2

    # Verify the first entry is the Document paradigm prediction
    assert logs[0]["payload_type"] == "JSON"
    assert logs[0]["raw_payload"] == mock_nosql_json_payload.strip()
    assert len(logs[0]["recommendations"]) == 1
    assert logs[0]["recommendations"][0]["predicted_paradigm"] == "Document"

    # Verify the second entry is the Relational paradigm prediction
    assert logs[1]["payload_type"] == "JSON"
    assert logs[1]["raw_payload"] == mock_json_payload.strip()
    assert len(logs[1]["recommendations"]) == 1
    assert logs[1]["recommendations"][0]["predicted_paradigm"] == "Relational"

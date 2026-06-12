from typing import Dict, Any, List
import json
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from .parsers import parse_json, parse_xml
from .extractors import extract_features
from .predictor import SchemaPredictor
from .models import AnalysisRequest, SchemaRecommendation
from .serializers import SchemaRecommendationSerializer, AnalysisHistorySerializer

class AnalyzeView(APIView):
    """
    POST /api/v1/analyze/
    I write this view to handle raw JSON or XML schema uploads. It extracts features,
    sends them to my ML predictors, and persists everything to the DB.
    """
    def post(self, request: Any) -> Response:
        raw_payload: str = request.data.get('raw_payload', '').strip()
        payload_type: str = request.data.get('payload_type', '').upper().strip()

        if not raw_payload:
            if isinstance(request.data, dict) and ('entities' in request.data or 'requirements' in request.data):
                raw_payload = json.dumps(request.data)
                if not payload_type:
                    payload_type = 'JSON'
            else:
                try:
                    body_str = request.body.decode('utf-8').strip()
                    if body_str:
                        try:
                            parsed_body = json.loads(body_str)
                            if isinstance(parsed_body, dict) and 'raw_payload' in parsed_body:
                                raw_payload = parsed_body.get('raw_payload', '').strip()
                                payload_type = parsed_body.get('payload_type', '').upper().strip()
                            else:
                                raw_payload = body_str
                        except json.JSONDecodeError:
                            raw_payload = body_str
                except Exception:
                    pass

        if not raw_payload:
            return Response(
                {"error": "raw_payload field is required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # I'll autodetect the format if the caller didn't specify it
        if not payload_type:
            if raw_payload.startswith('<'):
                payload_type = 'XML'
            else:
                payload_type = 'JSON'

        if payload_type not in ('JSON', 'XML'):
            return Response(
                {"error": "payload_type must be either 'JSON' or 'XML'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Start parsing the raw inputs
        try:
            if payload_type == 'JSON':
                parsed_data = parse_json(raw_payload)
            else:
                parsed_data = parse_xml(raw_payload)
        except ValidationError as e:
            # Capture any validation or XXE issues and send back a 400 response
            return Response(
                {"error": "Parsing failed", "details": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred during parsing: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Feed the parsed data into my feature extractor and model
        try:
            feature_df: pd.DataFrame = extract_features(parsed_data)
            predictor = SchemaPredictor()
            predictions: Dict[str, str] = predictor.predict_schema_needs(feature_df)
        except Exception as e:
            return Response(
                {"error": f"Feature extraction or model inference failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Save request and recommendation details to my DB logs
        try:
            analysis_request = AnalysisRequest.objects.create(
                payload_type=payload_type,
                raw_payload=raw_payload
            )
            recommendation = SchemaRecommendation.objects.create(
                request=analysis_request,
                predicted_paradigm=predictions.get('recommended_db_paradigm', 'Relational'),
                normalization_target=predictions.get('normalization_target', '3NF'),
                indexing_strategy=predictions.get('indexing_strategy', 'B-Tree_Heavy'),
                scaling_strategy=predictions.get('scaling_strategy', 'Vertical')
            )
            
            # Serialize and send back the recommendation results
            serializer = SchemaRecommendationSerializer(recommendation)
            return Response({
                "status": "success",
                "request_id": analysis_request.id,
                "recommendation": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to persist evaluation log to database: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommendationsListView(APIView):
    """
    GET /api/v1/recommendations/
    I write this view to fetch the history of all my schema analysis requests.
    """
    def get(self, request: Any) -> Response:
        try:
            # I prefetch recommendations here to keep query performance high and avoid N+1 queries
            history_logs = AnalysisRequest.objects.all().prefetch_related('recommendations').order_by('-created_at')
            serializer = AnalysisHistorySerializer(history_logs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve logs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

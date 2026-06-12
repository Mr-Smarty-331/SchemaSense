from rest_framework import serializers
from .models import AnalysisRequest, SchemaRecommendation

class SchemaRecommendationSerializer(serializers.ModelSerializer):
    generated_boilerplate = serializers.SerializerMethodField()

    class Meta:
        model = SchemaRecommendation
        fields = [
            'id',
            'predicted_paradigm',
            'normalization_target',
            'indexing_strategy',
            'scaling_strategy',
            'generated_boilerplate',
            'created_at'
        ]

    def get_generated_boilerplate(self, obj: SchemaRecommendation) -> str:
        """
        I run this to dynamically generate SQL or MongoDB schema code on-the-fly.
        It figures out the payload format and predicted paradigm, then generates the code.
        """
        try:
            raw_payload = obj.request.raw_payload
            payload_type = obj.request.payload_type
            
            # Let's parse the raw payload using my ingestion parsers
            from .parsers import parse_json, parse_xml
            if payload_type == 'JSON':
                parsed_data = parse_json(raw_payload)
            else:
                parsed_data = parse_xml(raw_payload)
                
            # Initialize and run my database schema code generator
            from .generators import BoilerplateGenerator
            generator = BoilerplateGenerator(parsed_data, obj.predicted_paradigm)
            return generator.generate()
        except Exception as e:
            return f"-- Error generating boilerplate: {str(e)}"

class AnalysisHistorySerializer(serializers.ModelSerializer):
    # I nested my recommendations inside the requests log representation
    recommendations = SchemaRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = AnalysisRequest
        fields = [
            'id',
            'payload_type',
            'raw_payload',
            'created_at',
            'recommendations'
        ]

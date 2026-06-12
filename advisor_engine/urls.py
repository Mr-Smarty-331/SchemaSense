from django.urls import path
from .views import AnalyzeView, RecommendationsListView

urlpatterns = [
    path('analyze/', AnalyzeView.as_view(), name='analyze'),
    path('recommendations/', RecommendationsListView.as_view(), name='recommendations'),
]

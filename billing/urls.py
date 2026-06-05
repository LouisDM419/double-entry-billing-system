from django.urls import path
from strawberry.django.views import GraphQLView
from billing.schema import schema
from billing.views import ingest_usage_event, dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("api/ingest", ingest_usage_event, name="ingest"),
    path("graphql", GraphQLView.as_view(schema=schema), name="graphql"),
]

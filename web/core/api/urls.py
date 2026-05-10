from django.urls import path

from core.api import views

urlpatterns = [
    path("sync/users/", views.sync_users, name="api_sync_users"),
    path("sync/traffic/", views.sync_traffic, name="api_sync_traffic"),
    path("nodes/join/", views.nodes_join, name="api_nodes_join"),
]


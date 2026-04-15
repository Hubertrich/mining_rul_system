from django.urls import path
from . import views

app_name = "frontend"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path("assets/", views.assets, name='assets'),
    path("select_asset/", views.select_asset, name='select_asset'),
    path("maintenance_logs/", views.maintenance_log, name='maintenance_logs'),
]
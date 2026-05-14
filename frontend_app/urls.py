from django.urls import path
from . import views

app_name = "frontend"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path("assets/", views.assets, name='assets'),
    path("asset_list/", views.asset_list, name='asset_list'),
    path("maintenance_logs/", views.maintenance_log, name='maintenance_logs'),
    path("analysis_overview/", views.analysis_overview, name='analysis_overview'),
    path("rul_modelling/", views.rul_modelling, name='rul_modelling'),
]
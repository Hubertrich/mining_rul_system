from django.shortcuts import render

def dashboard(request):
    return render(request, 'frontend/dashboard.html')

def assets(request):
    return render(request, 'frontend/assets.html')

def asset_list(request):
    return render(request, 'frontend/asset_list.html')

def maintenance_log(request):
    return render(request, 'frontend/maintenance_log.html')

def analysis_overview(request):
    return render(request, 'frontend/analysis_overview.html')

def rul_modelling(request):
    return render(request, 'frontend/rul_modelling.html')
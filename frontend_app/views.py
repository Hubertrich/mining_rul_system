from django.shortcuts import render

def dashboard(request):
    return render(request, 'frontend/dashboard.html')

def assets(request):
    return render(request, 'frontend/assets.html')

def select_asset(request):
    return render(request, 'frontend/select_asset.html')

def maintenance_log(request):
    return render(request, 'frontend/maintenance_log.html')
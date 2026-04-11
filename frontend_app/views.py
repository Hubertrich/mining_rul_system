from django.shortcuts import render

def dashboard(request):
    return render(request, 'frontend/dashboard.html')
from django.shortcuts import render
from django.http import HttpResponse
from .models import Doctor

# Create your views here.
def home(request):
    doctors = Doctor.objects.filter(is_active=True).order_by('name')

    context = {
        'clinic_name': 'Piki Ora Medical Center',
        'doctors': doctors,
    }
    return render(request, 'clinic/home.html', context)

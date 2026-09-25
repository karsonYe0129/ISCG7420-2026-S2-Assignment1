from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def home(request):
    context = {
        'clinic_name': 'Piki Ora Medical Center'
    }
    return render(request, 'clinic/home.html', context)

from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone

from .models import Doctor, Appointment

# Create your views here.
def home(request):
    doctors = Doctor.objects.filter(is_active=True).order_by('name')

    now = timezone.localtime()

    appointments = (
        Appointment.objects
        .filter(
            is_active=True,
            doctor__is_active=True
        )
        .filter(
            Q(date__gt=now.date())
            | Q(date=now.date(), start_time__gt=now.time())
        )
        .select_related('doctor')
    )

    context = {
        'clinic_name': 'Piki Ora Medical Center',
        'doctors': doctors,
        'appointments': appointments,
    }
    return render(request, 'clinic/home.html', context)

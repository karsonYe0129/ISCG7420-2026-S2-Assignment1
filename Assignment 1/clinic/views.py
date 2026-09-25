from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.shortcuts import render, redirect
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

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'clinic/register.html', {'form': form})

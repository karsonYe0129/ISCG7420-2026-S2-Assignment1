from django import forms
from django.utils import timezone
from django.db.models import Q

from .models import Appointment, Booking

class RescheduleBookingForm(forms.Form):
    appointment = forms.ModelChoiceField(
        queryset=Appointment.objects.none(),
        label='New appointment time',
        empty_label='Choose an available time',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        now = timezone.localtime()

        self.fields['appointment'].queryset = (
            Appointment.objects
            .filter(
                is_active=True,
                doctor__is_active=True,
            )
            .filter(
                Q(date__gt=now.date())
                | Q(
                    date=now.date(),
                    start_time__gt=now.time()
                )
            )
            .exclude(bookings__status='confirmed')
            .select_related('doctor')
        )

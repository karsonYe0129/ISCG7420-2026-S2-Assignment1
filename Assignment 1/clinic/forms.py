from django import forms
from django.utils import timezone
from django.db.models import Q

from .models import Appointment, Booking, Doctor

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

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'speciality', 'bio', 'is_active']
        labels = {
            'name': 'Doctor name',
            'speciality': 'Speciality',
            'bio': 'Bio',
            'is_active': 'Active',
        }

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['doctor', 'date', 'start_time', 'end_time', 'is_active']
        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
            'start_time': forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time'}
            ),
            'end_time': forms.TimeInput(
                format='%H:%M',
                attrs={'type': 'time'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['doctor'].queryset = (
            Doctor.objects
            .filter(is_active=True)
            .order_by('name')
        )

    def clean(self):
        cleaned_data = super().clean()

        doctor = cleaned_data.get('doctor')
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if not all([doctor, date, start_time, end_time]):
            return cleaned_data

        if end_time <= start_time:
            self.add_error(
                'end_time',
                'End time must be after start time'
            )
            return cleaned_data

        now = timezone.localtime()

        if(
            date < now.date()
            or (date == now.date() and start_time <= now.time())
        ):
            self.add_error(
                'date',
                'Choose a date and time in the future',
            )

        if cleaned_data.get('is_active'):
            overlapping = Appointment.objects.filter(
                doctor=doctor,
                date=date,
                is_active=True,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise forms.ValidationError(
                    'This doctor already has an overlapping active slot.'
                )

        return cleaned_data


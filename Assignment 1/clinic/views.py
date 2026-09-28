from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import RescheduleBookingForm, DoctorForm, AppointmentForm
from django.core.exceptions import PermissionDenied

from .models import Doctor, Appointment, Booking

# Create your views here.
def home(request):
    doctors = Doctor.objects.filter(is_active=True).order_by('name')

    now = timezone.localtime()

    appointments = (
        Appointment.objects
        .filter(is_active=True, doctor__is_active=True)
        .filter(
            Q(date__gt=now.date())
            | Q(date=now.date(), start_time__gt=now.time())
        )
        .exclude(bookings__status='confirmed')
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

@login_required
@require_POST
def book_appointment(request, appointment_id):
    try:
        with transaction.atomic():
            appointment = get_object_or_404(
                Appointment.objects.select_for_update(),
                pk=appointment_id,
            )

            now = timezone.localtime()
            has_started = (
                appointment.date < now.date()
                or(
                    appointment.date == now.date()
                    and appointment.start_time <= now.time()
                )
            )

            if(
                not appointment.is_active
                or not appointment.doctor.is_active
                or has_started
            ):
                messages.error(request, 'This slot is no longer available.')
                return redirect('home')

            Booking.objects.create(
                patient=request.user,
                appointment=appointment,
            )

    except IntegrityError:
        if not Booking.objects.filter(
            appointment_id=appointment_id,
            status='confirmed',
        ).exists():
            raise

        messages.error(request, 'This slot has already been booked.')

    else:
        messages.success(request, f'Booking confirmed: {appointment}')

    return redirect('home')

@login_required
def my_bookings(request):
    bookings = (
        Booking.objects
        .filter(patient=request.user)
        .select_related('appointment__doctor')
        .order_by('appointment__date', 'appointment__start_time')
    )

    return render(
        request,
        'clinic/my_bookings.html',
        {'bookings': bookings},
    )

@login_required
@require_POST
def cancel_booking(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects
            .select_for_update()
            .select_related('appointment'),
            pk=booking_id,
            patient=request.user,
        )

        if not booking.can_cancel:
            messages.error(
                request,
                'Only confirmed, upcoming bookings can be cancelled.'
            )
            return redirect('my_bookings')

        booking.status = 'cancelled'
        booking.save(update_fields=['status'])

    messages.success(request, 'Your booking has been cancelled.')
    return redirect('my_bookings')

@login_required
def reschedule_booking(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('appointment__doctor'),
        pk=booking_id,
        patient=request.user,
    )

    if not booking.can_cancel:
        messages.error(
            request,
            'Only confirmed, upcoming bookings can be rescheduled.'
        )
        return redirect('my_bookings')

    if request.method == 'POST':
        form = RescheduleBookingForm(request.POST)

        if form.is_valid():
            selected = form.cleaned_data['appointment']
            changed = False

            try:
                with transaction.atomic():
                    booking = get_object_or_404(
                        Booking.objects.select_for_update(),
                        pk=booking_id,
                        patient=request.user,
                    )

                    if not booking.can_cancel:
                        messages.error(
                            request,
                            'This booking can no longer be rescheduled.'
                        )
                        return redirect('my_bookings')

                    available = (
                        RescheduleBookingForm()
                        .fields['appointment']
                        .queryset
                    )
                    appointment = (
                        available.select_for_update()
                        .filter(pk=selected.pk)
                        .first()
                    )

                    if appointment is None:
                        form.add_error(
                            'appointment',
                            'This time is no longer available.'
                        )
                    else:
                        Booking.objects.filter(pk=booking.pk).update(
                            appointment=appointment,
                        )
                        changed = True

            except IntegrityError:
                if not Booking.objects.filter(
                    appointment_id=selected.pk,
                    status='confirmed',
                ).exists():
                    raise

                form.add_error(
                    'appointment',
                    'This time has just been booked. Choose another time.'
                )

            if changed:
                messages.success(
                    request,
                    'Your booking has been rescheduled.'
                )
                return redirect('my_bookings')

    else:
        form = RescheduleBookingForm()

    return render(
        request,
        'clinic/reschedule_booking.html',
        {'booking': booking, 'form': form}
    )

@login_required
def dashboard(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    User = get_user_model()

    context = {
        'doctor_count': Doctor.objects.count(),
        'appointment_count': Appointment.objects.count(),
        'confirmed_booking_count': Booking.objects.filter(
            status='confirmed'
        ).count(),
        'patient_count': User.objects.filter(
            is_staff=False,
            is_superuser=False,
        ).count(),
    }

    return render(request, 'clinic/dashboard.html', context)

@login_required
def manage_doctors(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    doctors = Doctor.objects.order_by('name')

    return render(
        request,
        'clinic/manage_doctors.html',
        {'doctors': doctors}
    )

@login_required
def doctor_create(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    if request.method == 'POST':
        form = DoctorForm(request.POST)

        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'{doctor.name} has been created.')
            return redirect('manage_doctors')

    else:
        form = DoctorForm()

    return render(
        request,
        'clinic/doctor_form.html',
        {
            'form': form,
            'page_title': 'Add Doctor',
        }
    )

@login_required
def doctor_edit(request, doctor_id):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    doctor = get_object_or_404(Doctor, pk=doctor_id)

    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)

        if form.is_valid():
            form.save()
            messages.success(request, f'{doctor.name} has been updated.')
            return redirect('manage_doctors')

    else:
        form = DoctorForm(instance=doctor)

    return render(
        request,
        'clinic/doctor_form.html',
        {
            'form': form,
            'page_title': 'Edit Doctor',
        }
    )

@login_required
def manage_appointments(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    appointments = (
        Appointment.objects
        .select_related('doctor')
        .order_by('date', 'start_time')
    )

    return render(
        request,
        'clinic/manage_appointments.html',
        {'appointments': appointments}
    )

@login_required
def appointment_create(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    if request.method == 'POST':
        form = AppointmentForm(request.POST)

        if form.is_valid():
            appointment = form.save()
            messages.success(request, f'{appointment.doctor.name} has been created.')
            return redirect('manage_appointments')

    else:
        form = AppointmentForm()

    return render(
        request,
        'clinic/appointment_form.html',
        {
            'form': form,
            'page_title': 'Add consultation slot',
        }
    )

@login_required
@transaction.atomic
def appointment_edit(request, appointment_id):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    appointment = get_object_or_404(
        Appointment.objects.select_for_update(),
        pk=appointment_id,
    )

    now = timezone.localtime()
    has_started = (
        appointment.date < now.date()
        or (
            appointment.date == now.date()
            and appointment.start_time <= now.time()
        )
    )

    if has_started:
        messages.error(request, 'Past or started slots cannot be edited.')
        return redirect('manage_appointments')

    if appointment.bookings.exists():
        messages.error(
            request,
            'This slot has booking records and cannot be edited.',
        )
        return redirect('manage_appointments')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)

        if form.is_valid():
            form.save()
            messages.success(request, 'The consultation slot has been updated.')
            return redirect('manage_appointments')
    else:
        form = AppointmentForm(instance=appointment)

    return render(
        request,
        'clinic/appointment_form.html',
        {
            'form': form,
            'page_title': 'Edit consultation slot',
        },
    )

@login_required
def manage_bookings(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    bookings = (
        Booking.objects
        .select_related('patient', 'appointment__doctor')
        .order_by('appointment__date', 'appointment__start_time', 'pk')
    )

    return render(
        request,
        'clinic/manage_bookings.html',
        {'bookings': bookings},
    )

@login_required
@require_POST
def admin_cancel_booking(request, booking_id):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update().select_related('appointment'),
            pk=booking_id,
        )

        if not booking.can_cancel:
            messages.error(
                request,
                'Only confirmed, upcoming bookings can be cancelled.',
            )
            return redirect('manage_bookings')

        booking.status = 'cancelled'
        booking.save(update_fields=['status'])

    messages.success(request, f'Booking #{booking.pk} has been cancelled.')
    return redirect('manage_bookings')

@login_required
def manage_patients(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    User = get_user_model()
    patients = User.objects.filter(
        is_staff=False,
        is_superuser=False,
    ).order_by('username')

    return render(
        request,
        'clinic/manage_patients.html',
        {'patients': patients},
    )

@login_required
@require_POST
def patient_set_status(request, patient_id):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied

    action = request.POST.get('action')
    if action not in ('activate', 'deactivate'):
        messages.error(request, 'Invalid action.')
        return redirect('manage_patients')

    User = get_user_model()

    with transaction.atomic():
        patient = get_object_or_404(
            User.objects.select_for_update(),
            pk=patient_id,
            is_staff=False,
            is_superuser=False,
        )
        patient.is_active = action == 'activate'
        patient.save(update_fields=['is_active'])

    status = 'activated' if patient.is_active else 'deactivated'
    messages.success(
        request,
        f'Patient account {patient.username} has been {status}.',
    )
    return redirect('manage_patients')


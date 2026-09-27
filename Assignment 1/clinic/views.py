from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import RescheduleBookingForm

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







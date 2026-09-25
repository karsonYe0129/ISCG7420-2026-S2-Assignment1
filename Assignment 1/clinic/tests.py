from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import Doctor, Appointment, Booking


class BookingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.patient_a = User.objects.create_user(username='patient_a')
        self.patient_b = User.objects.create_user(username='patient_b')

        doctor = Doctor.objects.create(
            name='Dr Test',
            speciality='General Practice',
        )
        self.appointment = Appointment.objects.create(
            doctor=doctor,
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )

    def test_first_booking_succeeds(self):
        booking = Booking.objects.create(
            patient=self.patient_a,
            appointment=self.appointment,
        )

        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(Booking.objects.count(), 1)

    def test_double_booking_is_rejected(self):
        Booking.objects.create(
            patient=self.patient_a,
            appointment=self.appointment,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Booking.objects.create(
                    patient=self.patient_b,
                    appointment=self.appointment,
                )

        self.assertEqual(Booking.objects.count(), 1)

    def test_cancelled_slot_can_be_booked_again(self):
        first_booking = Booking.objects.create(
            patient=self.patient_a,
            appointment=self.appointment,
        )
        first_booking.status = 'cancelled'
        first_booking.save(update_fields=['status'])

        Booking.objects.create(
            patient=self.patient_b,
            appointment=self.appointment,
        )

        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(
            Booking.objects.filter(status='confirmed').count(),
            1,
        )

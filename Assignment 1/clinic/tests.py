from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
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

class AdminAccessTests(TestCase):
    page_names = [
        'dashboard',
        'manage_doctors',
        'doctor_create',
        'manage_appointments',
        'appointment_create',
        'manage_bookings',
        'manage_patients',
    ]

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.patient = User.objects.create_user(
            username='test_patient',
        )
        cls.staff = User.objects.create_user(
            username='test_staff',
            is_staff=True,
        )

    def test_anonymous_users_are_redirected_to_login(self):
        for page_name in self.page_names:
            with self.subTest(page=page_name):
                url = reverse(page_name)
                response = self.client.get(url)

                self.assertRedirects(
                    response,
                    f"{reverse('login')}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_patients_cannot_access_admin_pages(self):
        self.client.force_login(self.patient)

        for page_name in self.page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 403)

    def test_staff_can_access_admin_pages(self):
        self.client.force_login(self.staff)

        for page_name in self.page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)

    def test_patient_cannot_deactivate_account(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse('patient_set_status', args=[self.patient.pk]),
            {'action': 'deactivate'},
        )

        self.assertEqual(response.status_code, 403)
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_active)

    def test_staff_can_deactivate_and_activate_patient(self):
        self.client.force_login(self.staff)
        url = reverse('patient_set_status', args=[self.patient.pk])

        for action, expected_active in [
            ('deactivate', False),
            ('activate', True),
        ]:
            with self.subTest(action=action):
                response = self.client.post(url, {'action': action})

                self.assertRedirects(response, reverse('manage_patients'))
                self.patient.refresh_from_db()
                self.assertEqual(self.patient.is_active, expected_active)

    def test_staff_cannot_deactivate_staff_account(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('patient_set_status', args=[self.staff.pk]),
            {'action': 'deactivate'},
        )

        self.assertEqual(response.status_code, 404)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_account_status_cannot_be_changed_by_get(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse('patient_set_status', args=[self.patient.pk]),
            {'action': 'deactivate'},
        )

        self.assertEqual(response.status_code, 405)
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_active)

class AdminCancelBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.patient = User.objects.create_user(username='cancel_patient')
        cls.staff = User.objects.create_user(
            username='cancel_staff',
            is_staff=True,
        )

        doctor = Doctor.objects.create(
            name='Dr Cancellation Test',
            speciality='General Practice',
        )
        cls.appointment = Appointment.objects.create(
            doctor=doctor,
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        cls.booking = Booking.objects.create(
            patient=cls.patient,
            appointment=cls.appointment,
        )

    def test_staff_can_cancel_upcoming_booking(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('admin_cancel_booking', args=[self.booking.pk]),
        )

        self.assertRedirects(response, reverse('manage_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    def test_patient_cannot_use_admin_cancel(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse('admin_cancel_booking', args=[self.booking.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

    def test_get_request_does_not_cancel_booking(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse('admin_cancel_booking', args=[self.booking.pk]),
        )

        self.assertEqual(response.status_code, 405)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

    def test_staff_cannot_cancel_past_booking(self):
        self.appointment.date = timezone.localdate() - timedelta(days=1)
        self.appointment.save(update_fields=['date'])
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('admin_cancel_booking', args=[self.booking.pk]),
        )

        self.assertRedirects(response, reverse('manage_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

class PatientBookingPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='booking_owner')
        cls.other_patient = User.objects.create_user(username='other_patient')

        doctor = Doctor.objects.create(
            name='Dr Permission Test',
            speciality='General Practice',
        )
        tomorrow = timezone.localdate() + timedelta(days=1)

        cls.original_slot = Appointment.objects.create(
            doctor=doctor,
            date=tomorrow,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        cls.new_slot = Appointment.objects.create(
            doctor=doctor,
            date=tomorrow,
            start_time=time(10, 0),
            end_time=time(10, 30),
        )
        cls.booking = Booking.objects.create(
            patient=cls.owner,
            appointment=cls.original_slot,
        )

    def test_owner_can_cancel_booking(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('cancel_booking', args=[self.booking.pk]),
        )

        self.assertRedirects(response, reverse('my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    def test_other_patient_cannot_cancel_booking(self):
        self.client.force_login(self.other_patient)

        response = self.client.post(
            reverse('cancel_booking', args=[self.booking.pk]),
        )

        self.assertEqual(response.status_code, 404)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

    def test_owner_can_reschedule_booking(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('reschedule_booking', args=[self.booking.pk]),
            {'appointment': self.new_slot.pk},
        )

        self.assertRedirects(response, reverse('my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.appointment_id, self.new_slot.pk)
        self.assertEqual(self.booking.patient_id, self.owner.pk)
        self.assertEqual(self.booking.status, 'confirmed')

    def test_other_patient_cannot_reschedule_booking(self):
        self.client.force_login(self.other_patient)
        url = reverse('reschedule_booking', args=[self.booking.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            url,
            {'appointment': self.new_slot.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.appointment_id, self.original_slot.pk)
        self.assertEqual(self.booking.patient_id, self.owner.pk)
        self.assertEqual(self.booking.status, 'confirmed')


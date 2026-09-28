from unicodedata import name

from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='clinic/login.html',
            redirect_authenticated_user=True,
        ),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path(
        'appointments/<int:appointment_id>/book/',
        views.book_appointment,
        name='book_appointment',
    ),
    path('my_bookings/', views.my_bookings, name='my_bookings'),

    path(
        'bookings/<int:booking_id>/cancel/',
        views.cancel_booking,
        name='cancel_booking',
    ),

    path(
        'bookings/<int:booking_id>/reschedule/',
        views.reschedule_booking,
        name='reschedule_booking',
    ),

    path('dashboard/', views.dashboard, name='dashboard'),

    path('dashboard/doctors/', views.manage_doctors, name='manage_doctors'),
    path('dashboard/doctors/add/', views.doctor_create, name='doctor_create'),

    path(
        'dashboard/doctors/<int:doctor_id>/edit/',
        views.doctor_edit,
        name='doctor_edit',
    ),
    path(
        'dashboard/appointments/',
        views.manage_appointments,
        name='manage_appointments',
    ),
    path(
        'dashboard/appointments/add/',
        views.appointment_create,
        name='appointment_create',
    ),

    path(
        'dashboard/appointments/<int:appointment_id>/edit/',
        views.appointment_edit,
        name='appointment_edit',
    ),

    path(
        'dashboard/bookings/',
        views.manage_bookings,
        name='manage_bookings',
    ),

path(
    'dashboard/bookings/<int:booking_id>/cancel/',
    views.admin_cancel_booking,
    name='admin_cancel_booking',
),

path(
    'dashboard/patients/',
    views.manage_patients,
    name='manage_patients',
),

path(
    'dashboard/patients/<int:patient_id>/status/',
    views.patient_set_status,
    name='patient_set_status',
),

]
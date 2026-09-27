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

]
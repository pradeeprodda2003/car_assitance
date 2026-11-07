from django.contrib import admin
from django.urls import path, include
from accounts.views import home_view
from cab_assistant.admin_views import admin_dashboard_view, admin_booking_action

urlpatterns = [
    # Built-in Django Admin
    path('admin/', admin.site.urls),

    # Custom Admin Analytics Portal
    path('admin-dashboard/', admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/action/<str:booking_id>/', admin_booking_action, name='admin_booking_action'),

    # Home Landing
    path('', home_view, name='home'),

    # Apps
    path('', include('accounts.urls')),
    path('', include('bookings.urls')),
    path('', include('drivers.urls')),
    path('', include('payments.urls')),
    path('', include('assistant_ai.urls')),
]

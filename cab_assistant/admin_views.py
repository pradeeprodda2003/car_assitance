from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json

from bookings.models import CabBooking, Rating, CabRate
from drivers.models import DriverProfile, Vehicle
from payments.models import Payment

User = get_user_model()


def is_portal_admin_user(user):
    return user.is_authenticated and (user.is_portal_admin or user.is_superuser or user.is_staff)


@login_required
@user_passes_test(is_portal_admin_user, login_url='login')
def admin_dashboard_view(request):
    """
    Comprehensive Admin Analytics & Management Dashboard powered by Chart.js.
    """
    # High-level KPIs
    total_users = User.objects.filter(role='CUSTOMER').count()
    total_drivers = DriverProfile.objects.count()
    active_drivers = DriverProfile.objects.filter(is_available=True).count()
    total_bookings = CabBooking.objects.count()
    completed_trips = CabBooking.objects.filter(status='COMPLETED').count()
    cancelled_trips = CabBooking.objects.filter(status='CANCELLED').count()
    active_trips = CabBooking.objects.filter(status__in=['REQUESTED', 'ACCEPTED', 'DRIVER_ARRIVING', 'STARTED']).count()

    total_revenue_aggr = CabBooking.objects.filter(status='COMPLETED').aggregate(total=Sum('final_fare'))
    total_revenue = total_revenue_aggr['total'] or 0.0

    avg_rating_aggr = Rating.objects.aggregate(avg=Avg('rating'))
    avg_rating = round(avg_rating_aggr['avg'] or 5.0, 1)

    # 1. Status Breakdown for Doughnut Chart
    status_counts = {
        'Completed': completed_trips,
        'Cancelled': cancelled_trips,
        'In Progress': active_trips,
    }
    status_chart_labels = list(status_counts.keys())
    status_chart_data = list(status_counts.values())

    # 2. Revenue & Trips by Cab Type
    cab_type_stats = {}
    for c_type in ['MINI', 'SEDAN', 'SUV', 'LUXURY']:
        c_bookings = CabBooking.objects.filter(cab_type=c_type)
        c_completed = c_bookings.filter(status='COMPLETED')
        rev = c_completed.aggregate(total=Sum('final_fare'))['total'] or 0.0
        cab_type_stats[c_type.title()] = {
            'count': c_bookings.count(),
            'revenue': float(rev)
        }

    cab_labels = list(cab_type_stats.keys())
    cab_trips = [cab_type_stats[k]['count'] for k in cab_labels]
    cab_revenues = [cab_type_stats[k]['revenue'] for k in cab_labels]

    # 3. 7-Day Trend
    today = timezone.localdate()
    days_labels = []
    days_bookings = []
    days_revenue = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        days_labels.append(day.strftime('%b %d'))
        day_qs = CabBooking.objects.filter(created_at__date=day)
        days_bookings.append(day_qs.count())
        rev_day = day_qs.filter(status='COMPLETED').aggregate(total=Sum('final_fare'))['total'] or 0.0
        days_revenue.append(float(rev_day))

    # Recent Data Tables
    recent_bookings = CabBooking.objects.all().select_related('customer', 'driver').order_by('-created_at')[:10]
    drivers_list = DriverProfile.objects.all().select_related('user', 'user__vehicle').order_by('-rating_avg')[:10]
    recent_ratings = Rating.objects.all().select_related('customer', 'driver', 'booking').order_by('-created_at')[:6]

    context = {
        'total_users': total_users,
        'total_drivers': total_drivers,
        'active_drivers': active_drivers,
        'total_bookings': total_bookings,
        'completed_trips': completed_trips,
        'cancelled_trips': cancelled_trips,
        'active_trips': active_trips,
        'total_revenue': total_revenue,
        'avg_rating': avg_rating,
        # Charts JSON
        'status_chart_labels': json.dumps(status_chart_labels),
        'status_chart_data': json.dumps(status_chart_data),
        'cab_labels': json.dumps(cab_labels),
        'cab_trips': json.dumps(cab_trips),
        'cab_revenues': json.dumps(cab_revenues),
        'days_labels': json.dumps(days_labels),
        'days_bookings': json.dumps(days_bookings),
        'days_revenue': json.dumps(days_revenue),
        # Tables
        'recent_bookings': recent_bookings,
        'drivers_list': drivers_list,
        'recent_ratings': recent_ratings,
    }
    return render(request, 'admin_portal/dashboard.html', context)


@login_required
@user_passes_test(is_portal_admin_user, login_url='login')
def admin_booking_action(request, booking_id):
    booking = get_object_or_404(CabBooking, booking_id=booking_id)
    action = request.POST.get('action')

    if action == 'cancel':
        booking.status = 'CANCELLED'
        booking.cancellation_reason = 'Cancelled by portal admin'
        booking.save()
        if booking.driver and hasattr(booking.driver, 'driver_profile'):
            booking.driver.driver_profile.is_available = True
            booking.driver.driver_profile.save(update_fields=['is_available'])
        messages.success(request, f"Booking {booking.booking_id} cancelled.")
    elif action == 'complete':
        booking.status = 'COMPLETED'
        booking.completed_at = timezone.now()
        booking.final_fare = booking.estimated_fare
        booking.save()
        messages.success(request, f"Booking {booking.booking_id} marked completed.")

    return redirect('admin_dashboard')

# core/admin.py
from django.contrib import admin
from .models import (
    Users,
    Grievances,
    MonthlyRatings,
    PartnerInvitations,
    RatingCategories,
    NotificationPreferences,
)

# Register all relevant models
admin.site.register(Users)
admin.site.register(Grievances)
admin.site.register(MonthlyRatings)
admin.site.register(PartnerInvitations)
admin.site.register(RatingCategories)
admin.site.register(NotificationPreferences)

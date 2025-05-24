from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("register/", views.register, name="register"),
    path(
        "registration-success/", views.registration_success, name="registration_success"
    ),
    path("login/", views.login_view, name="login"),
    path(
        "girlfriend-dashboard/", views.girlfriend_dashboard, name="girlfriend_dashboard"
    ),
    path("boyfriend-dashboard/", views.boyfriend_dashboard, name="boyfriend_dashboard"),
    path("link-partner/", views.link_partner, name="link_partner"),
    path("generate-invitation/", views.generate_invitation, name="generate_invitation"),
    path("enter-invitation/", views.enter_invitation, name="enter_invitation"),
    path("skip-invitation/", views.skip_invitation, name="skip_invitation"),
    path("dashboard/", views.redirect_to_dashboard, name="redirect_to_dashboard"),
    path("logout/", views.logout_view, name="logout"),
    path("edit-rating/<int:rating_id>/", views.edit_rating, name="edit_rating"),
    path("daily-logs/", views.daily_logs, name="daily_logs"),
    path("edit-daily-log/<int:log_id>/", views.edit_daily_log, name="edit_daily_log"),
    path(
        "delete-daily-log/<int:log_id>/",
        views.delete_daily_log,
        name="delete_daily_log",
    ),
    path("save-daily-log/<int:log_id>/", views.save_daily_log, name="save_daily_log"),
    path("grievances/", views.grievances, name="grievances"),
    path(
        "boyfriend-grievances/", views.boyfriend_grievances, name="boyfriend_grievances"
    ),
    path(
        "resolve-grievance/<int:grievance_id>/",
        views.resolve_grievance,
        name="resolve_grievance",
    ),
    path(
        "save-grievance/<int:grievance_id>/",
        views.save_grievance,
        name="save_grievance",
    ),
    path(
        "delete-grievance/<int:grievance_id>/",
        views.delete_grievance,
        name="delete_grievance",
    ),
    path(
        "update-resolution/<int:grievance_id>/",
        views.update_resolution,
        name="update_resolution",
    ),
    path("girlfriend-history/", views.girlfriend_history, name="girlfriend_history"),
    path("boyfriend-history/", views.boyfriend_history, name="boyfriend_history"),
    path("girlfriend-settings/", views.girlfriend_settings, name="girlfriend_settings"),
    path("boyfriend-settings/", views.boyfriend_settings, name="boyfriend_settings"),
]

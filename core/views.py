# core/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from .forms import DailyLogForm, GrievanceForm, UserRegistrationForm
from .models import DailyLogs, Grievances, MonthlyRatings, Users
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.shortcuts import render, redirect
import uuid
from datetime import date, timedelta, datetime, time
from django.utils import timezone
from .models import PartnerInvitations
from datetime import datetime
from django.contrib import messages
from .forms import MonthlyRatingForm
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from .models import Users, MonthlyRatings, DailyLogs, Grievances, PartnerInvitations
from django.utils import timezone
from django.db.models import Q


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password_hash = make_password(form.cleaned_data["password"])
            user.email_verified = False
            user.save()

            # Store user in session
            request.session["user_id"] = user.id
            request.session["username"] = user.username
            request.session["role"] = user.role

            return redirect("link_partner")
    else:
        form = UserRegistrationForm()

    return render(request, "core/register.html", {"form": form})


# Add this new view
def link_partner(request):
    if "user_id" not in request.session:
        return redirect("login")

    return render(request, "core/link_partner.html")


def registration_success(request):
    return render(request, "core/registration_success.html")


def landing_page(request):
    return render(request, "core/landing.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = Users.objects.get(username=username)
            if check_password(password, user.password_hash):
                # Store user in session
                request.session["user_id"] = user.id
                request.session["username"] = user.username
                request.session["role"] = user.role

                # Redirect to appropriate dashboard
                if user.role == "girlfriend":
                    return redirect("girlfriend_dashboard")
                else:
                    return redirect("boyfriend_dashboard")
            else:
                return render(
                    request,
                    "core/login.html",
                    {"error": "Invalid username or password"},
                )
        except Users.DoesNotExist:
            return render(
                request, "core/login.html", {"error": "Invalid username or password"}
            )

    return render(request, "core/login.html")


def boyfriend_dashboard(request):
    # Check if user is logged in
    if "user_id" not in request.session:
        return redirect("login")

    # Check if user is a boyfriend
    if request.session.get("role") != "boyfriend":
        return redirect("login")

    return render(request, "core/boyfriend_dashboard.html")


def generate_invitation(request):
    if "user_id" not in request.session:
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Check if user already has a partner
    if user.partner_id is not None:
        if user.role == "girlfriend":
            return redirect("girlfriend_dashboard")
        else:
            return redirect("boyfriend_dashboard")

    # Check if user already has an active invitation
    existing_invitation = PartnerInvitations.objects.filter(
        inviter_id=user_id, status="pending"
    ).first()

    if existing_invitation:
        invitation_code = existing_invitation.invitation_code
    else:
        # Generate a new invitation code
        invitation_code = uuid.uuid4().hex[:8].upper()
        expires_at = timezone.now() + timedelta(days=7)

        PartnerInvitations.objects.create(
            inviter_id=user_id,
            invitation_code=invitation_code,
            email="",  # Optional: can be filled if they provide partner's email
            status="pending",
            expires_at=expires_at,
        )

    return render(
        request, "core/generate_invitation.html", {"invitation_code": invitation_code}
    )


def enter_invitation(request):
    if "user_id" not in request.session:
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Check if user already has a partner
    if user.partner_id is not None:
        if user.role == "girlfriend":
            return redirect("girlfriend_dashboard")
        else:
            return redirect("boyfriend_dashboard")

    error = None

    if request.method == "POST":
        invitation_code = request.POST.get("invitation_code", "").strip().upper()

        try:
            invitation = PartnerInvitations.objects.get(
                invitation_code=invitation_code, status="pending"
            )

            # Check if the invitation has expired - FIX THE TIMEZONE ISSUE
            current_time = timezone.now()

            # Make teh expires_at timezone aware if it's naive
            invitation.expires_at = invitation.expires_at
            if invitation.expires_at.tzinfo is None:
                invitation.expires_at = timezone.make_aware(invitation.expires_at)

            # Check if invitation has expired
            if invitation.expires_at < current_time:
                error = "This invitation has expired. Please ask your partner to generate a new one."
            else:
                # Link partners
                partner = Users.objects.get(id=invitation.inviter_id)

                # Make sure they have opposite roles
                if user.role == partner.role:
                    error = f"Cannot link with another {user.role}. Please enter a code from your partner."
                else:
                    # Update both users
                    user.partner_id = partner.id
                    partner.partner_id = user.id

                    user.save()
                    partner.save()

                    # Update invitation status
                    invitation.status = "accepted"
                    invitation.save()

                    # Redirect to dashboard
                    if user.role == "girlfriend":
                        return redirect("girlfriend_dashboard")
                    else:
                        return redirect("boyfriend_dashboard")

        except PartnerInvitations.DoesNotExist:
            error = "Invalid invitation code. Please check and try again."

    return render(request, "core/enter_invitation.html", {"error": error})


def skip_invitation(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") == "girlfriend":
        return redirect("girlfriend_dashboard")
    else:
        return redirect("boyfriend_dashboard")


def redirect_to_dashboard(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") == "girlfriend":
        return redirect("girlfriend_dashboard")
    else:
        return redirect("boyfriend_dashboard")


def girlfriend_dashboard(request):
    # Check if user is logged in
    if "user_id" not in request.session:
        return redirect("login")

    # Check if user is a girlfriend
    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Get current date for month check
    current_date = datetime.now()
    current_month_start = datetime(current_date.year, current_date.month, 1)

    # Check if already rated this month
    existing_rating = None
    if partner:
        existing_rating = MonthlyRatings.objects.filter(
            from_user=user,
            to_user=partner,
            month__year=current_date.year,
            month__month=current_date.month,
        ).first()

    # Process form submission
    if request.method == "POST" and partner and not existing_rating:
        form = MonthlyRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.from_user = user
            rating.to_user = partner
            rating.month = current_month_start
            rating.status = "submitted"
            rating.save()

            messages.success(request, "Your rating has been submitted successfully!")
            return redirect("girlfriend_dashboard")
    else:
        form = MonthlyRatingForm()

    # Get rating history
    rating_history = []
    if partner:
        rating_history = MonthlyRatings.objects.filter(
            from_user=user, to_user=partner
        ).order_by("-month")[
            :6
        ]  # Show last 6 months

    # Get editable ratings (submitted but not edited)
    editable_ratings = []
    if partner:
        editable_ratings = MonthlyRatings.objects.filter(
            from_user=user,
            to_user=partner,
            status="submitted",  # Only ratings with 'submitted' status can be edited
        ).order_by("-month")

    context = {
        "user": user,
        "partner": partner,
        "form": form,
        "existing_rating": existing_rating,
        "rating_history": rating_history,
        "current_month": current_date.strftime("%B %Y"),
        "editable_ratings": editable_ratings,
    }

    return render(request, "core/girlfriend_dashboard.html", context)


# Add a new view for editing ratings
def edit_rating(request, rating_id):
    if "user_id" not in request.session:
        return redirect("login")

    # Check if user is a girlfriend
    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Get the rating
    try:
        rating = MonthlyRatings.objects.get(id=rating_id, from_user=user)

        # Check if rating is editable (status is 'submitted')
        if rating.status != "submitted":
            messages.error(
                request,
                "This rating has already been edited and cannot be changed again.",
            )
            return redirect("girlfriend_dashboard")

        if request.method == "POST":
            form = MonthlyRatingForm(request.POST, instance=rating)
            if form.is_valid():
                edited_rating = form.save(commit=False)
                edited_rating.status = "edited"  # Mark as edited
                edited_rating.save()

                messages.success(request, "Your rating has been updated successfully!")
                return redirect("girlfriend_dashboard")
        else:
            form = MonthlyRatingForm(instance=rating)

        return render(
            request, "core/edit_rating.html", {"form": form, "rating": rating}
        )

    except MonthlyRatings.DoesNotExist:
        messages.error(request, "Rating not found.")
        return redirect("girlfriend_dashboard")


def logout_view(request):
    # Clear session
    request.session.flush()
    return redirect("landing_page")


def boyfriend_dashboard(request):
    # Check if user is logged in
    if "user_id" not in request.session:
        return redirect("login")

    # Check if user is a boyfriend
    if request.session.get("role") != "boyfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Initialize variables first
    ratings = []
    latest_rating = None
    avg_score = 0
    recent_logs = []

    if partner:
        ratings = MonthlyRatings.objects.filter(
            from_user=partner, to_user=user
        ).order_by("-month")

        if ratings.exists():
            latest_rating = ratings.first()

            # Calculate average score
            total_score = sum(rating.overall_score for rating in ratings)
            avg_score = round(total_score / len(ratings), 1)

        recent_logs = []
        if partner:
            recent_logs = DailyLogs.objects.filter(
                from_user=partner, to_user=user
            ).order_by("-date")[:5]

    context = {
        "user": user,
        "partner": partner,
        "latest_rating": latest_rating,
        "ratings": ratings[:6],  # Last 6 ratings
        "avg_score": avg_score,
        "rating_count": len(ratings),
        "recent_logs": recent_logs,
    }

    return render(request, "core/boyfriend_dashboard.html", context)


def daily_logs(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Handle form submission
    if request.method == "POST" and partner:
        form = DailyLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.from_user = user
            log.to_user = partner
            log.created_at = timezone.now()
            log.updated_at = timezone.now()
            log.save()

            messages.success(request, "Your daily log has been saved!")
            return redirect("daily_logs")
    else:
        form = DailyLogForm()

    # Get existing logs grouped by month
    logs_by_month = {}
    if partner:
        logs = DailyLogs.objects.filter(from_user=user, to_user=partner).order_by(
            "-date"
        )

        for log in logs:
            month_key = log.date.strftime("%B %Y")
            if month_key not in logs_by_month:
                logs_by_month[month_key] = []
            logs_by_month[month_key].append(log)

    context = {
        "user": user,
        "partner": partner,
        "form": form,
        "logs_by_month": logs_by_month,
    }

    return render(request, "core/daily_logs.html", context)


# Can remove this function because edition is handled inline in the template
def edit_daily_log(request, log_id):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    try:
        log = DailyLogs.objects.get(id=log_id, from_user=user)

        if request.method == "POST":
            form = DailyLogForm(request.POST, instance=log)
            if form.is_valid():
                updated_log = form.save(commit=False)
                updated_log.updated_at = timezone.now()
                updated_log.save()

                messages.success(request, "Your log has been updated!")
                return redirect("daily_logs")
        else:
            form = DailyLogForm(instance=log)

        return render(request, "core/edit_daily_log.html", {"form": form, "log": log})

    except DailyLogs.DoesNotExist:
        messages.error(request, "Log not found.")
        return redirect("daily_logs")


def delete_daily_log(request, log_id):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    try:
        log = DailyLogs.objects.get(id=log_id, from_user=user)
        log.delete()
        messages.success(request, "Log deleted successfully!")
    except DailyLogs.DoesNotExist:
        messages.error(request, "Log not found.")

    return redirect("daily_logs")


from django.http import JsonResponse


def save_daily_log(request, log_id):
    if "user_id" not in request.session:
        return JsonResponse({"success": False, "error": "Not authenticated"})

    if request.session.get("role") != "girlfriend":
        return JsonResponse({"success": False, "error": "Not authorized"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    try:
        log = DailyLogs.objects.get(id=log_id, from_user=user)

        log_text = request.POST.get("log_text", "")
        mood = request.POST.get("mood", "")

        if log_text and mood:
            log.log_text = log_text
            log.mood = mood
            log.updated_at = timezone.now()
            log.save()

            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Missing data"})

    except DailyLogs.DoesNotExist:
        return JsonResponse({"success": False, "error": "Log not found"})


def grievances(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Handle form submission
    if request.method == "POST" and partner:
        form = GrievanceForm(request.POST)
        if form.is_valid():
            grievance = form.save(commit=False)
            grievance.from_user = user
            grievance.to_user = partner
            grievance.status = "new"
            grievance.created_at = timezone.now()
            grievance.updated_at = timezone.now()
            grievance.save()

            # Send email notification
            # if partner.email:
            #     # Create a severity display mapping
            #     severity_map = {
            #         1: "⚪ Minor issue - Just mentioning it",
            #         2: "🔵 Moderate - Please address this",
            #         3: "🟠 Important - Needs attention soon",
            #         4: "🔴 Urgent - Requires immediate attention",
            #         5: "⚫ Critical - Relationship threatening",
            #     }

            #     severity_display = severity_map.get(
            #         int(grievance.severity_level), f"Level {grievance.severity_level}"
            #     )

            #     subject = (
            #         f"New Grievance from {user.username} - Severity: {severity_display}"
            #     )
            #     message = f"""
            # Dear {partner.username},

            # Your girlfriend {user.username} has logged a new grievance:

            # Severity: Level {grievance.severity_level} ({severity_display})

            # Message:
            # {grievance.message}

            # Please log in to address this issue.

            # Best regards,
            # Girlfriend Rating System
            #     """
            #     send_mail(
            #         subject,
            #         message,
            #         settings.DEFAULT_FROM_EMAIL,
            #         [partner.email],
            #         fail_silently=False,
            #     )

            messages.success(
                request,
                "Your grievance has been logged and your boyfriend has been notified.",
            )
            return redirect("grievances")
    else:
        form = GrievanceForm()

    # Get existing grievances
    user_grievances = []
    if partner:
        user_grievances = Grievances.objects.filter(
            from_user=user, to_user=partner
        ).order_by("-created_at")

    context = {
        "user": user,
        "partner": partner,
        "form": form,
        "grievances": user_grievances,
    }

    return render(request, "core/grievances.html", context)


def boyfriend_grievances(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "boyfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Get grievances from partner
    grievances_list = []
    if partner:
        grievances_list = Grievances.objects.filter(
            from_user=partner, to_user=user
        ).order_by("-created_at")

    # Update status to 'viewed' for new grievances
    for grievance in grievances_list:
        if grievance.status == "new":
            grievance.status = "viewed"
            grievance.save()

    context = {"user": user, "partner": partner, "grievances": grievances_list}

    return render(request, "core/boyfriend_grievances.html", context)


def resolve_grievance(request, grievance_id):
    if "user_id" not in request.session:
        return JsonResponse({"success": False, "error": "Not authenticated"})

    if request.session.get("role") != "boyfriend":
        return JsonResponse({"success": False, "error": "Not authorized"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    user_id = request.session["user_id"]

    try:
        grievance = Grievances.objects.get(id=grievance_id, to_user_id=user_id)

        resolution_notes = request.POST.get("resolution_notes", "")

        if resolution_notes:
            grievance.status = "resolved"
            grievance.resolution_notes = resolution_notes
            grievance.updated_at = timezone.now()
            grievance.save()

            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Missing resolution notes"})

    except Grievances.DoesNotExist:
        return JsonResponse({"success": False, "error": "Grievance not found"})


def save_grievance(request, grievance_id):
    if "user_id" not in request.session:
        return JsonResponse({"success": False, "error": "Not authenticated"})

    if request.session.get("role") != "girlfriend":
        return JsonResponse({"success": False, "error": "Not authorized"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    user_id = request.session["user_id"]

    try:
        grievance = Grievances.objects.get(id=grievance_id, from_user_id=user_id)

        message = request.POST.get("message", "")
        severity_level = request.POST.get("severity_level", "")

        if message and severity_level:
            grievance.message = message
            grievance.severity_level = severity_level
            grievance.updated_at = timezone.now()
            grievance.save()

            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Missing data"})

    except Grievances.DoesNotExist:
        return JsonResponse({"success": False, "error": "Grievance not found"})


def delete_grievance(request, grievance_id):
    if "user_id" not in request.session:
        return JsonResponse({"success": False, "error": "Not authenticated"})

    if request.session.get("role") != "girlfriend":
        return JsonResponse({"success": False, "error": "Not authorized"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    user_id = request.session["user_id"]

    try:
        grievance = Grievances.objects.get(id=grievance_id, from_user_id=user_id)
        grievance.delete()

        return JsonResponse({"success": True})
    except Grievances.DoesNotExist:
        return JsonResponse({"success": False, "error": "Grievance not found"})


def update_resolution(request, grievance_id):
    if "user_id" not in request.session:
        return JsonResponse({"success": False, "error": "Not authenticated"})

    if request.session.get("role") != "boyfriend":
        return JsonResponse({"success": False, "error": "Not authorized"})

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    user_id = request.session["user_id"]

    try:
        grievance = Grievances.objects.get(
            id=grievance_id, to_user_id=user_id, status="resolved"
        )

        resolution_notes = request.POST.get("resolution_notes", "")

        if resolution_notes:
            grievance.resolution_notes = resolution_notes
            grievance.updated_at = timezone.now()
            grievance.save()

            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Missing resolution notes"})

    except Grievances.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Grievance not found or not resolved"}
        )


from datetime import datetime, time


def girlfriend_history(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Collect all activities
    activities = []

    if partner:
        # Get Monthly Ratings
        ratings = MonthlyRatings.objects.filter(
            from_user=user, to_user=partner
        ).order_by("-created_at")

        for rating in ratings:
            # Normalize the date to datetime
            if rating.created_at:
                rating_date = rating.created_at
            elif rating.month:
                # Convert date to datetime by adding midnight time
                rating_date = datetime.combine(rating.month, time.min)
            else:
                rating_date = datetime.now()  # fallback

            activities.append(
                {
                    "type": "rating",
                    "date": rating_date,
                    "data": rating,
                    "icon": "📊",
                    "title": f'Monthly Rating - {rating.month.strftime("%B %Y")}',
                    "content": f"Score: {rating.overall_score}/10",
                    "status": rating.status or "submitted",
                }
            )

        # Get Daily Logs
        logs = DailyLogs.objects.filter(from_user=user, to_user=partner).order_by(
            "-created_at"
        )

        for log in logs:
            mood_emoji = {
                "happy": "😊",
                "sad": "😔",
                "neutral": "😐",
                "excited": "🤩",
                "angry": "😡",
            }.get(log.mood, "😐")

            # Ensure log.created_at is datetime
            log_date = log.created_at
            if isinstance(log_date, date) and not isinstance(log_date, datetime):
                log_date = datetime.combine(log_date, time.min)

            activities.append(
                {
                    "type": "log",
                    "date": log_date,
                    "data": log,
                    "icon": mood_emoji,
                    "title": f'Daily Log - {log.date.strftime("%B %d, %Y")}',
                    "content": (
                        log.log_text[:100] + "..."
                        if len(log.log_text) > 100
                        else log.log_text
                    ),
                    "status": "completed",
                }
            )

        # Get Grievances
        grievances = Grievances.objects.filter(
            from_user=user, to_user=partner
        ).order_by("-created_at")

        for grievance in grievances:
            severity_colors = {1: "⚪", 2: "🔵", 3: "🟠", 4: "🔴", 5: "⚫"}

            # Ensure grievance.created_at is datetime
            grievance_date = grievance.created_at
            if isinstance(grievance_date, date) and not isinstance(
                grievance_date, datetime
            ):
                grievance_date = datetime.combine(grievance_date, time.min)

            activities.append(
                {
                    "type": "grievance",
                    "date": grievance_date,
                    "data": grievance,
                    "icon": "⚠️",
                    "title": f"Grievance - Severity {grievance.severity_level}",
                    "content": (
                        grievance.message[:100] + "..."
                        if len(grievance.message) > 100
                        else grievance.message
                    ),
                    "status": grievance.status,
                    "severity": severity_colors.get(grievance.severity_level, "⚪"),
                }
            )

    # Sort all activities by date (newest first) - now all dates are datetime objects
    activities.sort(key=lambda x: x["date"], reverse=True)

    # Calculate summary statistics
    stats = {
        "total_ratings": len([a for a in activities if a["type"] == "rating"]),
        "total_logs": len([a for a in activities if a["type"] == "log"]),
        "total_grievances": len([a for a in activities if a["type"] == "grievance"]),
        "avg_rating": 0,
        "resolved_grievances": len(
            [
                a
                for a in activities
                if a["type"] == "grievance" and a["status"] == "resolved"
            ]
        ),
        "total_activities": len(activities),
    }

    # Calculate average rating
    ratings_data = [
        a["data"].overall_score for a in activities if a["type"] == "rating"
    ]
    if ratings_data:
        stats["avg_rating"] = round(sum(ratings_data) / len(ratings_data), 1)

    context = {
        "user": user,
        "partner": partner,
        "activities": activities,
        "stats": stats,
    }

    return render(request, "core/girlfriend_history.html", context)


def boyfriend_history(request):
    if "user_id" not in request.session:
        return redirect("login")

    if (
        request.session.get("role") != "boyfriend"
    ):  # FIXED: Changed from "girlfriend" to "boyfriend"
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Collect all activities
    activities = []

    if partner:
        # Get Monthly Ratings (ratings received from girlfriend)
        ratings = MonthlyRatings.objects.filter(
            from_user=partner,
            to_user=user,  # FIXED: Changed to get ratings FROM partner TO user
        ).order_by("-created_at")

        for rating in ratings:
            # Normalize the date to datetime
            if rating.created_at:
                rating_date = rating.created_at
            elif rating.month:
                # Convert date to datetime by adding midnight time
                rating_date = datetime.combine(rating.month, time.min)
            else:
                rating_date = datetime.now()  # fallback

            activities.append(
                {
                    "type": "rating",
                    "date": rating_date,
                    "data": rating,
                    "icon": "📊",
                    "title": f'Monthly Rating Received - {rating.month.strftime("%B %Y")}',
                    "content": (
                        f"Score: {rating.overall_score}/10 - {rating.positives[:50]}..."
                        if hasattr(rating, "positives") and rating.positives
                        else f"Score: {rating.overall_score}/10"
                    ),
                    "status": rating.status or "submitted",
                }
            )

        # Get Daily Logs (logs written about him by girlfriend)
        logs = DailyLogs.objects.filter(
            from_user=partner, to_user=user
        ).order_by(  # FIXED: Changed to get logs FROM partner TO user
            "-created_at"
        )

        for log in logs:
            mood_emoji = {
                "happy": "😊",
                "sad": "😔",
                "neutral": "😐",
                "excited": "🤩",
                "angry": "😡",
            }.get(log.mood, "😐")

            # Ensure log.created_at is datetime
            log_date = log.created_at
            if isinstance(log_date, date) and not isinstance(log_date, datetime):
                log_date = datetime.combine(log_date, time.min)

            activities.append(
                {
                    "type": "log",
                    "date": log_date,
                    "data": log,
                    "icon": mood_emoji,
                    "title": f'Daily Log About You - {log.date.strftime("%B %d, %Y")}',
                    "content": (
                        log.log_text[:100] + "..."
                        if len(log.log_text) > 100
                        else log.log_text
                    ),
                    "status": "received",
                }
            )

        # Get Grievances (grievances filed against him)
        grievances = Grievances.objects.filter(
            from_user=partner,
            to_user=user,  # FIXED: Changed to get grievances FROM partner TO user
        ).order_by("-created_at")

        for grievance in grievances:
            severity_colors = {1: "⚪", 2: "🔵", 3: "🟠", 4: "🔴", 5: "⚫"}

            # Ensure grievance.created_at is datetime
            grievance_date = grievance.created_at
            if isinstance(grievance_date, date) and not isinstance(
                grievance_date, datetime
            ):
                grievance_date = datetime.combine(grievance_date, time.min)

            activities.append(
                {
                    "type": "grievance",
                    "date": grievance_date,
                    "data": grievance,
                    "icon": "⚠️",
                    "title": f"Grievance Against You - Severity {grievance.severity_level}",
                    "content": (
                        grievance.message[:100] + "..."
                        if len(grievance.message) > 100
                        else grievance.message
                    ),
                    "status": grievance.status,
                    "severity": severity_colors.get(grievance.severity_level, "⚪"),
                }
            )

    # Sort all activities by date (newest first) - now all dates are datetime objects
    activities.sort(key=lambda x: x["date"], reverse=True)

    # Calculate summary statistics
    stats = {
        "total_ratings": len([a for a in activities if a["type"] == "rating"]),
        "total_logs": len([a for a in activities if a["type"] == "log"]),
        "total_grievances": len([a for a in activities if a["type"] == "grievance"]),
        "avg_rating": 0,
        "resolved_grievances": len(
            [
                a
                for a in activities
                if a["type"] == "grievance" and a["status"] == "resolved"
            ]
        ),
        "pending_grievances": len(
            [
                a
                for a in activities
                if a["type"] == "grievance" and a["status"] in ["new", "viewed"]
            ]
        ),
        "total_activities": len(activities),
    }

    # Calculate average rating
    ratings_data = [
        a["data"].overall_score for a in activities if a["type"] == "rating"
    ]
    if ratings_data:
        stats["avg_rating"] = round(sum(ratings_data) / len(ratings_data), 1)

    context = {
        "user": user,
        "partner": partner,
        "activities": activities,
        "stats": stats,
    }

    return render(request, "core/boyfriend_history.html", context)


def girlfriend_settings(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "girlfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Get relationship stats if partner exists (exclude archived data)
    relationship_stats = {}
    if partner:
        relationship_stats = {
            "total_ratings": MonthlyRatings.objects.filter(
                from_user=user, to_user=partner, is_archived=False
            ).count(),
            "total_logs": DailyLogs.objects.filter(
                from_user=user, to_user=partner, is_archived=False
            ).count(),
            "total_grievances": Grievances.objects.filter(
                from_user=user, to_user=partner, is_archived=False
            ).count(),
            "days_together": (
                (timezone.now().date() - user.created_at.date()).days
                if user.created_at
                else 0
            ),
        }

    success_message = None
    error_message = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            # Update profile information
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            new_username = request.POST.get("username", "").strip()

            # Validation
            if not first_name or not last_name or not new_username:
                error_message = "All fields are required."
            elif len(new_username) < 3:
                error_message = "Username must be at least 3 characters long."
            elif (
                Users.objects.filter(username=new_username).exclude(id=user.id).exists()
            ):
                error_message = "Username already exists. Please choose another."
            else:
                # Update user
                user.first_name = first_name
                user.last_name = last_name
                user.username = new_username
                user.save()

                # Update session
                request.session["username"] = new_username

                success_message = "Profile updated successfully!"

        elif action == "change_password":
            # Change password
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            # Validation
            if not current_password or not new_password or not confirm_password:
                error_message = "All password fields are required."
            elif not check_password(current_password, user.password_hash):
                error_message = "Current password is incorrect."
            elif len(new_password) < 6:
                error_message = "New password must be at least 6 characters long."
            elif new_password != confirm_password:
                error_message = "New passwords do not match."
            else:
                # Update password
                user.password_hash = make_password(new_password)
                user.save()
                success_message = "Password changed successfully!"

        elif action == "break_up":
            # Enhanced breakup with data options
            confirmation = request.POST.get("break_up_confirmation", "")
            data_action = request.POST.get("data_action", "keep")

            if confirmation == "BREAK UP":
                if partner:
                    # Handle different data management options
                    if data_action == "delete":
                        # Delete all relationship data permanently
                        MonthlyRatings.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        DailyLogs.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        Grievances.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        success_message = f"Relationship ended with {partner.username}. All data has been permanently deleted."

                    elif data_action == "hide":
                        # Mark data as archived
                        MonthlyRatings.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        DailyLogs.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        Grievances.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        success_message = f"Relationship ended with {partner.username}. Data has been hidden and can be restored if you reconnect."

                    else:  # keep
                        success_message = f"Relationship ended with {partner.username}. Your history has been preserved."

                    # Clear partner relationships
                    user.partner_id = None
                    partner.partner_id = None
                    user.save()
                    partner.save()

                    partner = None  # Update local variable
                    relationship_stats = {}
                else:
                    error_message = "You are not currently in a relationship."
            else:
                error_message = "Please type 'BREAK UP' to confirm the breakup."

        elif action == "link_partner":
            # Link with new partner
            invitation_code = request.POST.get("invitation_code", "").strip().upper()

            if user.partner_id:
                error_message = (
                    "You are already in a relationship. Please break up first."
                )
            elif not invitation_code:
                error_message = "Please enter an invitation code."
            else:
                try:
                    invitation = PartnerInvitations.objects.get(
                        invitation_code=invitation_code, status="pending"
                    )

                    # Check if the invitation has expired
                    current_time = timezone.now()
                    if invitation.expires_at.tzinfo is None:
                        invitation.expires_at = timezone.make_aware(
                            invitation.expires_at
                        )

                    if invitation.expires_at < current_time:
                        error_message = "This invitation has expired. Please ask your partner to generate a new one."
                    else:
                        # Link partners
                        new_partner = Users.objects.get(id=invitation.inviter_id)

                        # Make sure they have opposite roles
                        if user.role == new_partner.role:
                            error_message = f"Cannot link with another {user.role}. Please enter a code from your partner."
                        else:
                            # Update both users
                            user.partner_id = new_partner.id
                            new_partner.partner_id = user.id
                            user.save()
                            new_partner.save()

                            # Update invitation status
                            invitation.status = "accepted"
                            invitation.save()

                            # Check if there's archived data with this partner and offer to restore
                            archived_ratings = MonthlyRatings.objects.filter(
                                Q(from_user=user, to_user=new_partner)
                                | Q(from_user=new_partner, to_user=user),
                                is_archived=True,
                            ).exists()

                            if archived_ratings:
                                success_message = f"Successfully linked with {new_partner.username}! You have archived relationship data - would you like to restore it?"
                            else:
                                success_message = (
                                    f"Successfully linked with {new_partner.username}!"
                                )

                            partner = new_partner  # Update local variable

                except PartnerInvitations.DoesNotExist:
                    error_message = (
                        "Invalid invitation code. Please check and try again."
                    )

        elif action == "restore_data":
            # Restore archived data
            if partner:
                MonthlyRatings.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                DailyLogs.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                Grievances.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                success_message = f"Successfully restored your relationship history with {partner.username}!"

    context = {
        "user": user,
        "partner": partner,
        "relationship_stats": relationship_stats,
        "success_message": success_message,
        "error_message": error_message,
    }

    return render(request, "core/girlfriend_settings.html", context)


def boyfriend_settings(request):
    if "user_id" not in request.session:
        return redirect("login")

    if request.session.get("role") != "boyfriend":
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)

    # Find the partner
    partner = None
    if user.partner_id:
        partner = Users.objects.get(id=user.partner_id)

    # Get relationship stats if partner exists (exclude archived data)
    relationship_stats = {}
    if partner:
        relationship_stats = {
            "total_ratings": MonthlyRatings.objects.filter(
                from_user=partner, to_user=user, is_archived=False
            ).count(),
            "total_logs": DailyLogs.objects.filter(
                from_user=partner, to_user=user, is_archived=False
            ).count(),
            "total_grievances": Grievances.objects.filter(
                from_user=partner, to_user=user, is_archived=False
            ).count(),
            "days_together": (
                (timezone.now().date() - user.created_at.date()).days
                if user.created_at
                else 0
            ),
        }

    success_message = None
    error_message = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            # Update profile information
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            new_username = request.POST.get("username", "").strip()

            # Validation
            if not first_name or not last_name or not new_username:
                error_message = "All fields are required."
            elif len(new_username) < 3:
                error_message = "Username must be at least 3 characters long."
            elif (
                Users.objects.filter(username=new_username).exclude(id=user.id).exists()
            ):
                error_message = "Username already exists. Please choose another."
            else:
                # Update user
                user.first_name = first_name
                user.last_name = last_name
                user.username = new_username
                user.save()

                # Update session
                request.session["username"] = new_username

                success_message = "Profile updated successfully!"

        elif action == "change_password":
            # Change password
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            # Validation
            if not current_password or not new_password or not confirm_password:
                error_message = "All password fields are required."
            elif not check_password(current_password, user.password_hash):
                error_message = "Current password is incorrect."
            elif len(new_password) < 6:
                error_message = "New password must be at least 6 characters long."
            elif new_password != confirm_password:
                error_message = "New passwords do not match."
            else:
                # Update password
                user.password_hash = make_password(new_password)
                user.save()
                success_message = "Password changed successfully!"

        elif action == "break_up":
            # Enhanced breakup with data options
            confirmation = request.POST.get("break_up_confirmation", "")
            data_action = request.POST.get("data_action", "keep")

            if confirmation == "BREAK UP":
                if partner:
                    # Handle different data management options
                    if data_action == "delete":
                        # Delete all relationship data permanently
                        MonthlyRatings.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        DailyLogs.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        Grievances.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).delete()

                        success_message = f"Relationship ended with {partner.username}. All data has been permanently deleted."

                    elif data_action == "hide":
                        # Mark data as archived
                        MonthlyRatings.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        DailyLogs.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        Grievances.objects.filter(
                            Q(from_user=user, to_user=partner)
                            | Q(from_user=partner, to_user=user)
                        ).update(is_archived=True, archived_at=timezone.now())

                        success_message = f"Relationship ended with {partner.username}. Data has been hidden and can be restored if you reconnect."

                    else:  # keep
                        success_message = f"Relationship ended with {partner.username}. Your history has been preserved."

                    # Clear partner relationships
                    user.partner_id = None
                    partner.partner_id = None
                    user.save()
                    partner.save()

                    partner = None  # Update local variable
                    relationship_stats = {}
                else:
                    error_message = "You are not currently in a relationship."
            else:
                error_message = "Please type 'BREAK UP' to confirm the breakup."

        elif action == "link_partner":
            # Link with new partner
            invitation_code = request.POST.get("invitation_code", "").strip().upper()

            if user.partner_id:
                error_message = (
                    "You are already in a relationship. Please break up first."
                )
            elif not invitation_code:
                error_message = "Please enter an invitation code."
            else:
                try:
                    invitation = PartnerInvitations.objects.get(
                        invitation_code=invitation_code, status="pending"
                    )

                    # Check if the invitation has expired
                    current_time = timezone.now()
                    if invitation.expires_at.tzinfo is None:
                        invitation.expires_at = timezone.make_aware(
                            invitation.expires_at
                        )

                    if invitation.expires_at < current_time:
                        error_message = "This invitation has expired. Please ask your partner to generate a new one."
                    else:
                        # Link partners
                        new_partner = Users.objects.get(id=invitation.inviter_id)

                        # Make sure they have opposite roles
                        if user.role == new_partner.role:
                            error_message = f"Cannot link with another {user.role}. Please enter a code from your partner."
                        else:
                            # Update both users
                            user.partner_id = new_partner.id
                            new_partner.partner_id = user.id
                            user.save()
                            new_partner.save()

                            # Update invitation status
                            invitation.status = "accepted"
                            invitation.save()

                            # Check if there's archived data with this partner and offer to restore
                            archived_ratings = MonthlyRatings.objects.filter(
                                Q(from_user=user, to_user=new_partner)
                                | Q(from_user=new_partner, to_user=user),
                                is_archived=True,
                            ).exists()

                            if archived_ratings:
                                success_message = f"Successfully linked with {new_partner.username}! You have archived relationship data - would you like to restore it?"
                            else:
                                success_message = (
                                    f"Successfully linked with {new_partner.username}!"
                                )

                            partner = new_partner  # Update local variable

                except PartnerInvitations.DoesNotExist:
                    error_message = (
                        "Invalid invitation code. Please check and try again."
                    )

        elif action == "restore_data":
            # Restore archived data
            if partner:
                MonthlyRatings.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                DailyLogs.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                Grievances.objects.filter(
                    Q(from_user=user, to_user=partner)
                    | Q(from_user=partner, to_user=user),
                    is_archived=True,
                ).update(is_archived=False, archived_at=None)

                success_message = f"Successfully restored your relationship history with {partner.username}!"

    context = {
        "user": user,
        "partner": partner,
        "relationship_stats": relationship_stats,
        "success_message": success_message,
        "error_message": error_message,
    }

    return render(request, "core/boyfriend_settings.html", context)


def break_up_with_options(request):
    """Enhanced breakup function with data management options"""
    if "user_id" not in request.session:
        return redirect("login")

    user_id = request.session["user_id"]
    user = Users.objects.get(id=user_id)
    partner = Users.objects.get(id=user.partner_id) if user.partner_id else None

    if not partner:
        return JsonResponse({"success": False, "error": "No partner found"})

    if request.method == "POST":
        confirmation = request.POST.get("break_up_confirmation", "")
        data_action = request.POST.get("data_action", "keep")  # keep, archive, delete

        if confirmation != "BREAK UP":
            return JsonResponse(
                {"success": False, "error": "Please type 'BREAK UP' to confirm"}
            )

        # Handle different data management options
        if data_action == "delete":
            # Delete all relationship data permanently
            MonthlyRatings.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).delete()

            DailyLogs.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).delete()

            Grievances.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).delete()

            success_message = f"Relationship ended with {partner.username}. All data has been permanently deleted."

        elif data_action == "archive":
            # Mark data as archived (add is_archived field to models)
            MonthlyRatings.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).update(is_archived=True, archived_at=timezone.now())

            DailyLogs.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).update(is_archived=True, archived_at=timezone.now())

            Grievances.objects.filter(
                Q(from_user=user, to_user=partner) | Q(from_user=partner, to_user=user)
            ).update(is_archived=True, archived_at=timezone.now())

            success_message = f"Relationship ended with {partner.username}. Data has been archived and can be restored if you reconnect."

        else:  # keep
            success_message = f"Relationship ended with {partner.username}. Your history has been preserved."

        # Clear partner relationships
        user.partner_id = None
        partner.partner_id = None
        user.save()
        partner.save()

        return JsonResponse({"success": True, "message": success_message})

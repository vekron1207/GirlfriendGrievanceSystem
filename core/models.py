from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Users(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=[
        ('girlfriend', 'Girlfriend'),
        ('boyfriend', 'Boyfriend'),
    ])
    partner = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username


class RatingCategories(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'rating_categories'
        verbose_name_plural = 'Rating Categories'

    def __str__(self):
        return self.name


class MonthlyRatings(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('archived', 'Archived'),
    ]
    
    from_user = models.ForeignKey(Users, on_delete=models.CASCADE)
    to_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='received_ratings')
    month = models.DateField()
    positives = models.TextField(blank=True, null=True)
    negatives = models.TextField(blank=True, null=True)
    overall_score = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'monthly_ratings'
        unique_together = [['from_user', 'month']]
        verbose_name_plural = 'Monthly Ratings'

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.month})"


class DailyLogs(models.Model):
    MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('neutral', 'Neutral'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('excited', 'Excited'),
    ]
    
    from_user = models.ForeignKey(Users, on_delete=models.CASCADE)
    to_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='received_logs')
    date = models.DateField()
    log_text = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'daily_logs'
        verbose_name_plural = 'Daily Logs'

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.date})"


class Grievances(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    SEVERITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    
    from_user = models.ForeignKey(Users, on_delete=models.CASCADE)
    to_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='received_grievances')
    message = models.TextField()
    severity_level = models.IntegerField(choices=SEVERITY_CHOICES, default=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    resolution_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'grievances'
        verbose_name_plural = 'Grievances'

    def __str__(self):
        return f"Grievance from {self.from_user.username} to {self.to_user.username}"


class PartnerInvitations(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    inviter = models.ForeignKey(Users, on_delete=models.CASCADE)
    invitation_code = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'partner_invitations'
        verbose_name_plural = 'Partner Invitations'

    def __str__(self):
        return f"Invitation from {self.inviter.username} to {self.email}"


class NotificationPreferences(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE)
    rating_reminder = models.BooleanField(default=True)
    grievance_notification = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Notifications for {self.user.username}"
from datetime import datetime
from django import forms
from .models import DailyLogs, Grievances, MonthlyRatings, Users


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    ROLE_CHOICES = (("girlfriend", "Girlfriend"), ("boyfriend", "Boyfriend"))
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = Users
        fields = ["username", "email", "role"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data


class MonthlyRatingForm(forms.ModelForm):
    positives = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "What did your boyfriend do well this month?",
            }
        ),
        required=True,
    )
    negatives = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 5, "placeholder": "What could your boyfriend improve on?"}
        ),
        required=True,
    )
    overall_score = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(
            attrs={
                "type": "range",
                "min": 1,
                "max": 10,
                "step": 1,
                "class": "rating-slider",
                "list": "rating-values",
            }
        ),
    )

    class Meta:
        model = MonthlyRatings
        fields = ["positives", "negatives", "overall_score"]


class DailyLogForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), initial=datetime.now().date()
    )
    log_text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "What did your boyfriend do today? Log a special moment, a sweet gesture, or something to remember.",
            }
        )
    )
    MOOD_CHOICES = [
        ("happy", "😊 Happy"),
        ("neutral", "😐 Neutral"),
        ("sad", "😔 Sad"),
        ("excited", "🤩 Excited"),
        ("angry", "😡 Angry"),
    ]
    mood = forms.ChoiceField(
        choices=MOOD_CHOICES, required=True, widget=forms.RadioSelect
    )

    class Meta:
        model = DailyLogs
        fields = ["date", "log_text", "mood"]


class GrievanceForm(forms.ModelForm):
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Describe your grievance. Be specific about what's bothering you.",
            }
        )
    )

    SEVERITY_CHOICES = [
        (1, "⚪ Minor issue - Just mentioning it"),
        (2, "🔵 Moderate - Please address this"),
        (3, "🟠 Important - Needs attention soon"),
        (4, "🔴 Urgent - Requires immediate attention"),
        (5, "⚫ Critical - Relationship threatening"),
    ]

    severity_level = forms.ChoiceField(
        choices=SEVERITY_CHOICES, widget=forms.RadioSelect, initial=3
    )

    class Meta:
        model = Grievances
        fields = ["message", "severity_level"]

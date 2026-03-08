from django.forms import ModelForm
from .models import Room, Student, Booking
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

class BookingForm(ModelForm):
    class Meta:
        model = Booking
        fields = ["usage_date", "start_time", "end_time"]
        widgets = {
            'usage_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_usage_date(self):
        from datetime import date
        usage_date = self.cleaned_data.get('usage_date')
        if usage_date and usage_date < date.today():
            raise forms.ValidationError("Cannot select past dates.")
        return usage_date

    def clean(self):
        from datetime import date, datetime
        cleaned_data = super().clean()
        usage_date = cleaned_data.get('usage_date')
        start_time = cleaned_data.get('start_time')
        if usage_date and start_time:
            if usage_date == date.today() and start_time < datetime.now().time():
                self.add_error('start_time', "Cannot select past times for today.")
        return cleaned_data

class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = ["gender", "faculty", "major", "year"]

class RoomForm(ModelForm):
    class Meta:
        model = Room
        fields = ["room_number", "capacity"]


from django import forms
from .models import Feedback, Student


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(i, i) for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }

User = get_user_model()

class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=Student.GENDER_CHOICES)
    faculty = forms.ChoiceField(choices=Student.FACULTY_CHOICES)
    major = forms.ChoiceField(choices=Student.MAJOR_CHOICES)
    year = forms.ChoiceField(choices=Student.YEAR_CHOICES)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2"
        ]

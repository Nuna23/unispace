from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=200,blank=True,null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["username"]

class Employee(models.Model):

    DEPARTMENT_CHOICES = [
        ("Academic Staff","Academic Staff"),
        ("Professional Staff","Professional Staff")
    ]

    user = models.OneToOneField(User,on_delete=models.CASCADE)
    department = models.CharField(max_length=200,choices=DEPARTMENT_CHOICES)

    def __str__(self):
        return self.user.email

class Student(models.Model):

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    YEAR_CHOICES = [
        (1, "Year 1"),
        (2, "Year 2"),
        (3, "Year 3"),
        (4, "Year 4"),
    ]
    FACULTY_CHOICES = [
        ("Engineering", "Engineering"),
        ("Applied Science", "Applied Science"),
        ("Applied Arts", "Applied Arts"),
        ("Architecture and Design", "Architecture and Design"),
    ]
    MAJOR_CHOICES = [
        ("Computer Engineering", "Computer Engineering"),
        ("Mechanical Engineering", "Mechanical Engineering"),
        ("Electrical Engineering Technology", "Electrical Engineering Technology"),
        ("Computer Science", "Computer Science"),
        ("English for Business and Industry Communication", "English for Business and Industry Communication"),
        ("Humanities", "Humanities"),
        ("Architecture", "Architecture"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=50, choices=GENDER_CHOICES)
    faculty = models.CharField(max_length=200, choices=FACULTY_CHOICES)
    major = models.CharField(max_length=200, choices=MAJOR_CHOICES)
    year = models.IntegerField(choices=YEAR_CHOICES)

    def __str__(self):
        return self.user.email

class Ban_History(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200,null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    
    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError("End date must be after start date.")
    
    def __str__(self):
        return self.reason

class Room(models.Model):
    room_number = models.CharField(max_length=10,unique=True)
    capacity = models.IntegerField()

    def __str__(self):
        return self.room_number

class Facility(models.Model):

    STATUS_CHOICES = [
        ("available","Available"),
        ("maintenance","Maintenance"),
        ("closed","Closed")
    ]

    facility_name = models.CharField(max_length=200)
    capacity = models.IntegerField()
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)

    def __str__(self):
        return self.facility_name


class Equipment(models.Model):

    CATEGORY_CHOICES = [
        ('SPORT', 'Sports Equipment'),
        ('ACADEMIC', 'Academic Equipment'),
        ('ACTIVITY', 'Activity Equipment'),
    ]

    equipment_name = models.CharField(max_length=200)
    category = models.CharField(max_length=200,choices=CATEGORY_CHOICES)
    total_quantity = models.IntegerField()
    available_quantity = models.IntegerField()

    def __str__(self):
        return self.equipment_name

class BookingEquipment(models.Model):
    booking = models.ForeignKey("Booking", on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.booking.id} - {self.equipment.equipment_name} x{self.quantity}"

class Booking(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    equipment = models.ManyToManyField(Equipment, through="BookingEquipment" , blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE,null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE,null=True, blank=True)
    usage_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    participants = models.ManyToManyField(Student,related_name="participants",blank=True)
    is_attended = models.BooleanField(default=False)

    def __str__(self):
        if self.room:
            item = f"Room: {self.room.room_number}"
        elif self.facility:
            item = f"Facility: {self.facility.facility_name}"
        else:
            item = f"Equipment: {self.total_equipment_quantity()} items"

        return f"{self.student.user.email} - {item} ({self.usage_date})"
    
    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")

        if self.pk:
            total = self.total_equipment_quantity()
            if total > 3:
                raise ValidationError("You can book at most 3 equipment items.")
    
    def total_equipment_quantity(self):
        return sum(
            item.quantity for item in self.bookingequipment_set.all()
        )


class Feedback(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],null=True, blank=True)
    comment = models.TextField()
    
    def __str__(self):
        return self.comment[:50]
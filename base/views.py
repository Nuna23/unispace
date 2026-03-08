from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from datetime import datetime, timedelta, date
import base64
import qrcode
import io

from .forms import StudentForm, RoomForm, RegisterForm, FeedbackForm , BookingForm
from .models import Room, Equipment, Facility, Booking, Student, Feedback,User, Ban_History

def loginPage(request):
    page = "login"
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email").lower()
        password = request.POST.get("password")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
            user = None
        user = authenticate(request, email=email, password=password)
        if user is not None:
            try:
                student = Student.objects.get(user=user)
                today = date.today()
                active_ban = Ban_History.objects.filter(
                    student=student,
                    start_date__lte=today,
                    end_date__gte=today
                ).first()
                if active_ban:
                    message = f"Your account is banned from {active_ban.start_date} to {active_ban.end_date}."
                    if active_ban.reason:
                        message += f" Reason: {active_ban.reason}."
                    message += " Please contact admin."
                    messages.error(request, message)
                else:
                    login(request, user)
                    return redirect('home')
            except Student.DoesNotExist:
                # If not a student, allow login (e.g., admin)
                login(request, user)
                return redirect('home')
        else:
            messages.error(request, "email or password does not exist")
    context = {"page": page}
    return render(request, "login_register.html", context)

def logoutUser(request):
    logout(request)
    return redirect("login")

def registerPage(request):
    form = RegisterForm()

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            email = data['email'].lower()
            password = data['password1']
            # create user
            user = User.objects.create_user(
                email=email,
                username=email,
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=password,
            )
            # create student profile
            Student.objects.create(
                user=user,
                gender=data['gender'],
                faculty=data['faculty'],
                major=data['major'],
                year=data['year'],
            )
            login(request, user)
            return redirect("home")
    return render(request, "login_register.html", {'form': form, 'page': 'register'})

@login_required(login_url="login")
def home(request):
    q = request.GET.get("q") if request.GET.get("q") != None else ""
    filter_type = request.GET.get("filter")
    
    rooms = Room.objects.all()
    facilities = Facility.objects.all()
    equipment = Equipment.objects.all()
    
    if q:
        rooms = rooms.filter(room_number__icontains=q)
        facilities = facilities.filter(facility_name__icontains=q)
        equipment = equipment.filter(equipment_name__icontains=q)
    
    if filter_type:
        if filter_type == 'all_rooms':
            facilities = Facility.objects.none()
            equipment = Equipment.objects.none()
        elif filter_type == 'booked_rooms':
            # Rooms that have bookings
            booked_room_ids = Booking.objects.filter(room__isnull=False).values_list('room_id', flat=True).distinct()
            rooms = rooms.filter(id__in=booked_room_ids)
            facilities = Facility.objects.none()
            equipment = Equipment.objects.none()
        elif filter_type == 'all_facilities':
            rooms = Room.objects.none()
            equipment = Equipment.objects.none()
        elif filter_type == 'booked_facilities':
            # facility that have bookings
            booked_facility_ids = Booking.objects.filter(facility__isnull=False).values_list('facility_id', flat=True).distinct()
            facilities = facilities.filter(id__in=booked_facility_ids)
            rooms = Room.objects.none()
            equipment = Equipment.objects.none()
        elif filter_type == 'all_equipment':
            rooms = Room.objects.none()
            facilities = Facility.objects.none()
        elif filter_type == 'available_equipment':
            equipment = equipment.filter(available_quantity__gt=0)
            rooms = Room.objects.none()
            facilities = Facility.objects.none()
    
    room_count = rooms.count()
    facility_count = facilities.count()
    equipment_count = equipment.count()
    context = {
        "rooms": rooms,
        "facilities": facilities,
        "equipment": equipment,
        "room_count": room_count,
        "facility_count": facility_count,
        "equipment_count": equipment_count,
        "query": q,
        "filter": filter_type,
    }
    return render(request, "home.html", context)

@login_required(login_url="login")
def userProfile(request, pk=None):
    # show profile of pk or current user if no pk provided
    if pk:
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('home')
    else:
        user = request.user
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None
    bookings = Booking.objects.filter(student=student).order_by('-created_at') if student else []
    context = {'student': student, 'bookings': bookings}
    return render(request, "profile.html", context)


@login_required(login_url="login")
def updateUser(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "You must complete your student profile first.")
        return redirect('home')
    
    bookings = Booking.objects.filter(student=student).order_by('-created_at')
    
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('update-user')
    else:
        form = StudentForm(instance=student)
    
    context = {'student': student, 'form': form, 'editing': request.GET.get('edit') == '1', 'bookings': bookings}
    return render(request, 'update-user.html', context)

@login_required(login_url="login")
def room(request, pk):
    room = Room.objects.get(id=pk)
    times = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    from datetime import datetime, date
    current_time = datetime.now().time()
    today = date.today()
    disabled_times = set()
    booked_slots = set()
    for time_slot in times:
        start_str = time_slot.split('-')[0]
        start_time = datetime.strptime(start_str, '%H:%M').time()
        if start_time < current_time:
            disabled_times.add(time_slot)
    
    # Get booked slots for today
    bookings_today = Booking.objects.filter(room=room, usage_date=today)
    for booking in bookings_today:
        slot = f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
        booked_slots.add(slot)
    
    # Get feedbacks for this room, ordered by newest first
    feedbacks = Feedback.objects.filter(booking__room=room).order_by('-created_at')
    can_feedback = False
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            booking = Booking.objects.filter(student=student, room=room, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
            if booking:
                can_feedback = True
        except Student.DoesNotExist:
            pass
    bookings = []
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            bookings = Booking.objects.filter(student=student)
        except Student.DoesNotExist:
            pass
    context = {"room": room, "times": times, "disabled_times": disabled_times, "booked_slots": booked_slots, "feedbacks": feedbacks, "can_feedback": can_feedback, "bookings": bookings}
    return render(request, "room.html", context)

@login_required(login_url="login")
def bookingRoom(request, pk):
    room = Room.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "You must complete your student profile before booking.")
        return redirect('update-user')

    initial = {}
    if request.method == "GET":
        time = request.GET.get("time")
        if time:
            parts = time.split("-")
            if len(parts) == 2:
                initial['start_time'] = parts[0]
                initial['end_time'] = parts[1]
        form = BookingForm(initial=initial)
    elif request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = student
            booking.room = room
            booking.save()
            messages.success(request, "Room booked successfully.")
            return redirect('booking-detail', pk=booking.id)
    return render(request, "booking_room.html", {"form": form, "room": room})

@login_required(login_url="login")
def bookingFacility(request, pk):
    facility = Facility.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "You must complete your student profile before booking.")
        return redirect('update-user')

    initial = {}
    if request.method == "GET":
        time = request.GET.get("time")
        if time:
            parts = time.split("-")
            if len(parts) == 2:
                initial['start_time'] = parts[0]
                initial['end_time'] = parts[1]
        form = BookingForm(initial=initial)
    elif request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = student
            booking.facility = facility
            booking.save()
            messages.success(request, "Facility booked successfully.")
            return redirect('booking-detail', pk=booking.id)
    return render(request, "booking_facility.html", {"form": form, "facility": facility})

@login_required(login_url="login")
def facility(request, pk):
    facility = Facility.objects.get(id=pk)
    times = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    from datetime import datetime, date
    current_time = datetime.now().time()
    today = date.today()
    disabled_times = set()
    booked_slots = set()
    for time_slot in times:
        end_str = time_slot.split('-')[1]
        end_time = datetime.strptime(end_str, '%H:%M').time()
        if end_time <= current_time:
            disabled_times.add(time_slot)
    
    # Get booked slots for today
    bookings_today = Booking.objects.filter(facility=facility, usage_date=today)
    for booking in bookings_today:
        slot = f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
        booked_slots.add(slot)
    
    # Get feedbacks for this facility, ordered by newest first
    feedbacks = Feedback.objects.filter(booking__facility=facility).order_by('-created_at')
    can_feedback = False
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            booking = Booking.objects.filter(student=student, facility=facility, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
            if booking:
                can_feedback = True
        except Student.DoesNotExist:
            pass
    bookings = []
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            bookings = Booking.objects.filter(student=student)
        except Student.DoesNotExist:
            pass
    context = {"facility": facility, "times": times, "disabled_times": disabled_times, "booked_slots": booked_slots, "feedbacks": feedbacks, "can_feedback": can_feedback, "bookings": bookings}
    return render(request, "facility.html", context)


@login_required(login_url="login")
def facilityFeedback(request, pk):
    facility = Facility.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile required to leave feedback.")
        return redirect('facility', pk=pk)

    booking = Booking.objects.filter(facility=facility, student=student, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
    if not booking:
        messages.error(request, "No eligible booking found to leave feedback.")
        return redirect('facility', pk=pk)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.booking = booking
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('facility', pk=pk)
    else:
        form = FeedbackForm()
    return render(request, 'feedback_form.html', {'form': form, 'facility': facility})

@login_required(login_url="login")
def equipmentFeedback(request, pk):
    equipment = Equipment.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile required to leave feedback.")
        return redirect('equipment', pk=pk)

    booking = Booking.objects.filter(equipment=equipment, student=student, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
    if not booking:
        messages.error(request, "No eligible booking found to leave feedback.")
        return redirect('equipment', pk=pk)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.booking = booking
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('equipment', pk=pk)
    else:
        form = FeedbackForm()
    return render(request, 'feedback_form.html', {'form': form, 'equipment': equipment})

@login_required(login_url="login")
def roomFeedback(request, pk):
    room = Room.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "Student profile required to leave feedback.")
        return redirect('room', pk=pk)

    booking = Booking.objects.filter(room=room, student=student, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
    if not booking:
        messages.error(request, "No eligible booking found to leave feedback.")
        return redirect('room', pk=pk)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = student
            feedback.booking = booking
            feedback.save()
            messages.success(request, "Feedback submitted.")
            return redirect('room', pk=pk)
    else:
        form = FeedbackForm()
    return render(request, 'feedback_form.html', {'form': form, 'room': room})

@login_required(login_url="login")
def equipment(request, pk):
    equipment = Equipment.objects.get(id=pk)
    times = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]
    from datetime import datetime, date
    current_time = datetime.now().time()
    today = date.today()
    disabled_times = set()
    booked_slots = set()
    for time_slot in times:
        start_str = time_slot.split('-')[0]
        start_time = datetime.strptime(start_str, '%H:%M').time()
        if start_time < current_time:
            disabled_times.add(time_slot)
    
    # Get booked quantities for today
    bookings_today = Booking.objects.filter(equipment=equipment, usage_date=today)
    slot_quantities = {}
    for booking in bookings_today:
        slot = f"{booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
        quantity = booking.bookingequipment_set.filter(equipment=equipment).first().quantity
        slot_quantities[slot] = slot_quantities.get(slot, 0) + quantity
    
    for slot, qty in slot_quantities.items():
        if qty >= equipment.available_quantity:
            booked_slots.add(slot)
    
    # Get feedbacks for this equipment, ordered by newest first
    feedbacks = Feedback.objects.filter(booking__equipment=equipment).order_by('-created_at')
    can_feedback = False
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            booking = Booking.objects.filter(student=student, equipment=equipment, is_attended=True).exclude(feedback__isnull=False).order_by('-usage_date').first()
            if booking:
                can_feedback = True
        except Student.DoesNotExist:
            pass
    bookings = []
    if request.user.is_authenticated:
        try:
            student = Student.objects.get(user=request.user)
            bookings = Booking.objects.filter(student=student)
        except Student.DoesNotExist:
            pass
    context = {"equipment": equipment, "times": times, "disabled_times": disabled_times, "booked_slots": booked_slots, "feedbacks": feedbacks, "can_feedback": can_feedback, "bookings": bookings}
    return render(request, "equipment.html", context)

@login_required(login_url="login")
def bookingEquipment(request, pk):
    equipment = Equipment.objects.get(id=pk)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, "You must complete your student profile before booking.")
        return redirect('update-user')

    initial = {}
    if request.method == "GET":
        time = request.GET.get("time")
        if time:
            parts = time.split("-")
            if len(parts) == 2:
                initial['start_time'] = parts[0]
                initial['end_time'] = parts[1]
        form = BookingForm(initial=initial)
    elif request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = student
            booking.save()
            booking.equipment.add(equipment, through_defaults={'quantity': 1})
            messages.success(request, "Equipment booking created successfully.")
            return redirect('booking-detail', pk=booking.id)
    return render(request, "booking_equipment.html", {"form": form, "equipment": equipment})

@login_required(login_url="login")
def bookingDetail(request, pk):
    booking = Booking.objects.get(id=pk)
    if booking.student.user != request.user:
        messages.error(request, "Access denied")
        return redirect('profile')
    current_time = datetime.now()
    booking_datetime = datetime.combine(booking.usage_date, booking.start_time)
    booking_end_datetime = datetime.combine(booking.usage_date, booking.end_time)
    show_qr = current_time >= booking_datetime and current_time <= booking_end_datetime
    qr_code = None
    if show_qr:
        qr_data = f"Booking ID: {booking.id} - Attended"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()
    feedbacks = Feedback.objects.filter(booking=booking).order_by('-created_at')
    if request.method == "POST":
        if not booking.is_attended:
            booking.is_attended = True
            booking.save()
            messages.success(request, "Attendance confirmed")
            return redirect('booking-detail', pk=booking.id)
    context = {'booking': booking, 'qr_code': qr_code, 'show_qr': show_qr, 'feedbacks': feedbacks}
    return render(request, 'booking_detail.html', context)

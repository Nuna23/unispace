from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.loginPage, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("register/", views.registerPage, name="register"),
    path("", views.home, name="home"),

    path("profile/<str:pk>", views.userProfile, name="user-profile"),
    path("profile", views.userProfile, name="profile"), 
    path("update-user", views.updateUser, name="update-user"),
    
    path("room/<int:pk>", views.room, name="room"),
    path("room/<int:pk>/feedback", views.roomFeedback, name="room-feedback"),
    path("facility/<int:pk>", views.facility, name="facility"),
    path("facility/<int:pk>/feedback", views.facilityFeedback, name="facility-feedback"),
    path("equipment/<int:pk>", views.equipment, name="equipment"),
    path("equipment/<int:pk>/feedback", views.equipmentFeedback, name="equipment-feedback"),
    
    path("booking-room/<int:pk>", views.bookingRoom, name="bookingRoom"),
    path("booking-facility/<int:pk>", views.bookingFacility, name="bookingFacility"),
    path("booking-equipment/<int:pk>", views.bookingEquipment, name="bookingEquipment"),
    path("booking/<int:pk>", views.bookingDetail, name="booking-detail"),


]
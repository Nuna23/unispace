from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User,Employee,Student,Ban_History,Room,Facility,Equipment,BookingEquipment,Booking,Feedback

admin.site.register(User, UserAdmin)
admin.site.register(Employee)
admin.site.register(Student)

@admin.register(Ban_History)
class BanHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'reason', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('student__user__email', 'reason')

admin.site.register(Room)
admin.site.register(Facility)
admin.site.register(Equipment)
admin.site.register(BookingEquipment)
admin.site.register(Booking)
admin.site.register(Feedback)


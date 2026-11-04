from django.contrib import admin
from .models import AcademicGroup, Course, Department, StudentProfile
from .models import Category, Ticket
from .models import Equipment, EquipmentReservation, ReservationEvent

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "category",
        "status", "owner", "created_at"
    )
    list_filter = ("status", "category")
    search_fields = ("title",)


@admin.register(AcademicGroup)
class AcademicGroupAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'department',
    )
    list_filter = (
        'department',
    )
    search_fields = (
        'name',
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'department')
    list_filter = ('department',)
    search_fields = ('title',)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department')
    list_filter = ('department',)
    search_fields = ('user__username',)
    filter_horizontal = ('courses',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'total_q', 'available_q')
    readonly_fields = ('available_q',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('total_q', 'available_q')
        return ('available_q',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.available_q = obj.total_q
        super().save_model(request, obj, form, change)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EquipmentReservation)
class EquipmentReservationAdmin(ReadOnlyAdmin):
    list_display = ('id', 'purpose', 'equipment', 'quantity', 'status', 'owner', 'created_at', 'deleted_at',)
    list_filter = ('status', 'equipment',)


@admin.register(ReservationEvent)
class ReservationEventAdmin(ReadOnlyAdmin):
    list_display = ('id', 'reservation', 'action', 'actor', 'created_at',)
    list_filter = ('action',)
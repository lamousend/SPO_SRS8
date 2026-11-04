from django.contrib import admin

from .models import ActivityEvent


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'section', 'object_repr')
    list_filter = ('action', 'section')
    search_fields = ('user__username', 'object_repr')
    date_hierarchy = 'created_at'

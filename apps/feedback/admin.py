from django.contrib import admin
from unfold.admin import ModelAdmin
from feedback.models import JourneyRating, SupportIssue, InternalBookingNote, BookingTimeline


@admin.register(JourneyRating)
class JourneyRatingAdmin(ModelAdmin):
    list_display = ('request', 'rating', 'rated_by', 'passenger_name', 'created_at')
    list_filter = ('rating',)
    search_fields = ('request__request_number', 'comments', 'passenger_name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('request', 'rated_by')


@admin.register(SupportIssue)
class SupportIssueAdmin(ModelAdmin):
    list_display = ('request', 'issue_type', 'status', 'reported_by', 'resolved_by', 'created_at')
    list_filter = ('status', 'issue_type')
    search_fields = ('request__request_number', 'description', 'resolution_notes')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('request', 'reported_by', 'resolved_by')


@admin.register(InternalBookingNote)
class InternalBookingNoteAdmin(ModelAdmin):
    list_display = ('request', 'author', 'created_at')
    search_fields = ('request__request_number', 'note', 'author__username')
    readonly_fields = ('created_at',)
    raw_id_fields = ('request', 'author')


@admin.register(BookingTimeline)
class BookingTimelineAdmin(ModelAdmin):
    list_display = ('request', 'action_type', 'previous_status', 'new_status', 'actor', 'timestamp')
    list_filter = ('action_type',)
    search_fields = ('request__request_number', 'description')
    readonly_fields = ('timestamp',)
    raw_id_fields = ('request', 'actor')

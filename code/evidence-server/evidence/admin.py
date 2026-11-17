from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from .models import PANEL, REVIEWER, Assignment, Audit, Exam, Session


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "source_site", "cmid", "quiz_id", "enabled", "retention_days")
    list_filter = ("source_site", "enabled")


class AssignmentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(
            is_active=True, groups__name__in=[REVIEWER, PANEL]).distinct()

    def clean(self):
        data = super().clean()
        if data.get("session") and data["session"].state == Session.State.PURGING:
            raise ValidationError("该会话正在删除。")
        return data


class Assignments(admin.TabularInline):
    model = Assignment
    form = AssignmentForm
    extra = 1


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("exam", "attempt", "state", "created_at", "expires_at")
    list_filter = ("state", "exam")
    search_fields = ("attempt", "student_ref")
    readonly_fields = [field.name for field in Session._meta.fields]
    inlines = [Assignments]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("when", "action", "session_ref", "actor")
    search_fields = ("session_ref",)
    readonly_fields = ("when", "action", "session_ref", "actor")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

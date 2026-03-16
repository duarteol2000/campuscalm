from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import ClassGroup, ParentProfile, StudentProfile, TeacherAssignment, User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("email",)
    list_display = (
        "email",
        "name",
        "role",
        "institution",
        "preferred_language",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active", "preferred_language", "institution")
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Informações pessoais e contexto institucional",
            {"fields": ("name", "phone_number", "institution", "role", "preferred_language")},
        ),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2", "institution", "role", "preferred_language", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "coach_enabled",
        "gender",
        "has_avatar",
        "allow_email",
        "allow_whatsapp",
        "allow_sms",
        "consent_at",
    )
    list_filter = ("plan", "coach_enabled", "gender", "allow_email", "allow_whatsapp", "allow_sms")

    @admin.display(boolean=True, description="Avatar")
    def has_avatar(self, obj):
        return bool(obj.avatar)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "institution",
        "status",
        "account_type",
        "enrollment_number",
        "grade_level",
        "class_group",
        "class_group_ref",
        "is_active_for_institution",
        "graduated_at",
    )
    list_filter = ("status", "account_type", "institution")
    search_fields = ("user__email", "user__name", "enrollment_number")


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student", "relationship_type", "institution", "created_at")
    list_filter = ("relationship_type", "institution")
    search_fields = ("user__email", "student__user__email", "student__user__name")


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "grade_level", "institution", "created_at")
    list_filter = ("institution", "grade_level")
    search_fields = ("name", "grade_level", "institution__nome_fantasia", "institution__razao_social")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "class_group", "institution", "created_at")
    list_filter = ("institution", "class_group__grade_level")
    search_fields = ("teacher__email", "teacher__name", "class_group__name", "class_group__grade_level")

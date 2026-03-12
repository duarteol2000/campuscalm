from rest_framework.permissions import BasePermission

from accounts.models import ParentProfile, StudentProfile, User


INSTITUTION_STAFF_ROLES = {
    User.ROLE_TEACHER,
    User.ROLE_COORDINATOR,
    User.ROLE_INSTITUTION_ADMIN,
}


def has_same_institution(user, institution_id: int | None) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return bool(user.institution_id and institution_id and user.institution_id == institution_id)


def can_view_rankings(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.role in INSTITUTION_STAFF_ROLES


def can_view_student_profile(user, student_profile: StudentProfile) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not has_same_institution(user, student_profile.institution_id):
        return False
    if user.role == User.ROLE_STUDENT:
        return student_profile.user_id == user.id
    if user.role == User.ROLE_PARENT:
        return ParentProfile.objects.filter(
            user=user,
            institution_id=student_profile.institution_id,
            student=student_profile,
        ).exists()
    return user.role in INSTITUTION_STAFF_ROLES


class HasInstitutionAccess(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_institutional_access())


class CanViewInstitutionRankings(BasePermission):
    def has_permission(self, request, view):
        return can_view_rankings(request.user)


class CanViewStudentRecord(BasePermission):
    student_lookup_kwarg = "student_profile"

    def has_object_permission(self, request, view, obj):
        return can_view_student_profile(request.user, obj)

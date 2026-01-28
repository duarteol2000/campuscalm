from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from utils.constants import COURSE_STATUS_CHOICES, COURSE_IN_PROGRESS, SEMESTER_STATUS_CHOICES, SEMESTER_ACTIVE


class Semester(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="semesters")
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=SEMESTER_STATUS_CHOICES, default=SEMESTER_ACTIVE)

    def __str__(self):
        return self.name


class Course(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    teacher = models.CharField(max_length=200, blank=True)
    credits = models.PositiveIntegerField(null=True, blank=True)
    passing_grade = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("7.0"))
    status = models.CharField(max_length=20, choices=COURSE_STATUS_CHOICES, default=COURSE_IN_PROGRESS)
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Assessment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=200)
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.0"))
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"), validators=[MinValueValidator(0)])
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SemesterCheckin(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="checkins")
    created_at = models.DateTimeField(auto_now_add=True)
    overall_stress = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.semester.name} checkin"

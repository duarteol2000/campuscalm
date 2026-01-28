from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from utils.constants import TASK_STATUS_CHOICES, TASK_TODO


class Task(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    stress_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    status = models.CharField(max_length=10, choices=TASK_STATUS_CHOICES, default=TASK_TODO)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

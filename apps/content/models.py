from django.db import models

from utils.constants import CONTENT_CATEGORY_CHOICES


class GuidedContent(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CONTENT_CATEGORY_CHOICES)
    duration_minutes = models.PositiveIntegerField()
    body_text = models.TextField()
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

from django.conf import settings
from django.db import models

from utils.constants import ACCESS_STATUS_CHOICES, ACCESS_PENDING, PLAN_CHOICES, REQUESTER_TYPE_CHOICES


class AccessRequest(models.Model):
    requester_email = models.EmailField()
    requester_name = models.CharField(max_length=255, blank=True)
    requester_type = models.CharField(max_length=20, choices=REQUESTER_TYPE_CHOICES)
    institution_name = models.CharField(max_length=255, blank=True)
    estimated_users = models.PositiveIntegerField(null=True, blank=True)
    wants_features = models.JSONField(default=list)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ACCESS_STATUS_CHOICES, default=ACCESS_PENDING)
    recommended_plan = models.CharField(max_length=10, choices=PLAN_CHOICES, blank=True)
    decided_plan = models.CharField(max_length=10, choices=PLAN_CHOICES, blank=True)
    created_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.requester_email


class AITriageLog(models.Model):
    access_request = models.ForeignKey(AccessRequest, on_delete=models.CASCADE, related_name="triage_logs")
    model_name = models.CharField(max_length=100)
    input_payload = models.JSONField()
    output_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.access_request.id} - {self.model_name}"

from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User, UserProfile


# Bloco: Criacao automatica de perfil
@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "phone": instance.phone_number or "",
                "plan": UserProfile.PLAN_FREE,
                "allow_whatsapp": True,
                "allow_sms": False,
                "allow_email": True,
            },
        )

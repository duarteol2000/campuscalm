from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        from billing.signals import seed_plans

        post_migrate.connect(seed_plans, sender=self)

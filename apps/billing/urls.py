from django.urls import path

from billing.views import CurrentPlanView, SetPlanView

urlpatterns = [
    path("plan/", CurrentPlanView.as_view(), name="billing-plan"),
    path("set-plan/", SetPlanView.as_view(), name="billing-set-plan"),
]

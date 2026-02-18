"""Services for brain domain."""

from .insights_service import build_dashboard_insights
from .notifications_service import maybe_send_absence_email

__all__ = ["build_dashboard_insights", "maybe_send_absence_email"]

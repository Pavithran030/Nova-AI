from sqlalchemy.orm import Session
from app.models.recovery_action import RecoveryAction
from datetime import datetime

def execute_action(action_type: str, entity_type: str, entity_id: str) -> dict:
    channel_map = {
        "delay_retry": ("api_retry", "Scheduled retry for next salary date within NPCI window"),
        "immediate_retry_with_backoff": ("api_retry", "Immediate retry with 30s backoff"),
        "send_update_link": ("whatsapp", "Sent card update link via WhatsApp"),
        "trigger_reauth": ("email", "Re-authorization request sent via email"),
        "auto_appeal": ("api", "Auto-appeal submitted with evidence package"),
        "immediate_retry_exponential": ("api_retry", "Retry with exponential backoff"),
        "checkout_nudge": ("sms", "Checkout reminder SMS sent with resume link"),
        "b2b_follow_up": ("whatsapp", "Payment follow-up sent via WhatsApp"),
        "ESCALATE_TO_HUMAN": ("human_queue", "Flagged for human review — classifier confidence below operating threshold"),
    }
    channel, content = channel_map.get(action_type, ("api", "Default action executed"))
    return {"channel": channel, "content_sent": content}

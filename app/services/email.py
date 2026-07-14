import requests
from flask import current_app

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> bool:
    """Best-effort email send — never raises. A missing key or a flaky network
    call should never break the page that triggered it (a trade, a page view)."""
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        current_app.logger.info("RESEND_API_KEY not set — skipping email to %s", to)
        return False

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": current_app.config.get("EMAIL_FROM"),
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=8,
        )
        if resp.status_code >= 400:
            current_app.logger.warning("Resend email failed (%s): %s", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as e:
        current_app.logger.warning("Resend email request failed: %s", e)
        return False

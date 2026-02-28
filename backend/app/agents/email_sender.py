"""Email Sender Agent — composes and sends job application emails via Gmail API."""

import os
import json
import structlog
from typing import Optional
from app.core.llm_router import get_llm

logger = structlog.get_logger()


async def compose_application_email(
    job_data: dict,
    cv_data: dict,
    hr_contact: dict,
    cover_letter: Optional[str] = None,
    linkedin_url: Optional[str] = None,
) -> dict:
    """Compose a professional application email.

    Returns:
        Dict with email_subject and email_body.
    """
    from app.core.skills import get_combined_skills

    llm = get_llm(task="email_composition")
    
    # Load relevant skills
    skills_context = get_combined_skills([
        "email-writing",
        "tone-guidelines"
    ])

    hr_name = hr_contact.get("hr_name", "Hiring Manager")
    job_title = job_data.get("title", "the open position")
    company = job_data.get("company", "your company")
    candidate_name = cv_data.get("personal_info", {}).get("name", "the candidate")
    linkedin_line = f"\n- LinkedIn: {linkedin_url}" if linkedin_url else ""

    prompt = f"""You are an elite Career Communication Specialist.

{skills_context}

TASK: Compose a high-performance job application email following the SKILLS and RULES provided above.

CRITICAL CONSTRAINTS:
1. Use the AIDA framework (Attention, Interest, Desire, Action).
2. Subject line must use one of the proven formulas from the skills.
3. Keep the email under 160 words.
4. No filler phrases (e.g., "I hope this email finds you well").
5. Include a specific, low-friction CTA.
6. If a LinkedIn URL is provided, naturally include it as a hyperlink or plain URL in the email signature or closing line (e.g., "linkedin.com/in/...").

Details:
- Candidate: {candidate_name}
- Position: {job_title}
- Company: {company}
- HR Contact: {hr_name}{linkedin_line}
- Cover letter basis: {(cover_letter or "")[:1000]}

Return JSON:
{{
    "email_subject": "Subject line following proven formula",
    "email_body": "Email body following AIDA framework",
    "tone_analysis": "Brief note on tone calibration used"
}}

Return ONLY valid JSON.
"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)
    except Exception as e:
        logger.error("email_compose_error", error=str(e))
        linkedin_sig = f"\nLinkedIn: {linkedin_url}" if linkedin_url else ""
        return {
            "email_subject": f"Application for {job_title} - {candidate_name}",
            "email_body": (
                f"Dear {hr_name},\n\n"
                f"I am writing to express my interest in the {job_title} position at {company}. "
                f"Please find my resume attached for your review.\n\n"
                f"I look forward to hearing from you.\n\n"
                f"Best regards,\n{candidate_name}{linkedin_sig}"
            ),
        }


async def send_via_gmail(
    user_tokens: dict,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: str = "Tailored_CV.pdf",
) -> dict:
    """Send email via Gmail API using user's OAuth tokens.

    Falls back to env-configured credentials (GOOGLE_REFRESH_TOKEN) when
    user_tokens doesn't contain client_id / client_secret.

    Returns:
        Dict with message_id and status.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from app.config import settings

        # Resolve client credentials — prefer tokens dict, fall back to settings
        client_id = (
            user_tokens.get("client_id")
            or settings.GOOGLE_OAUTH_CLIENT_ID
            or None
        )
        client_secret = (
            user_tokens.get("client_secret")
            or settings.GOOGLE_OAUTH_CLIENT_SECRET
            or None
        )
        refresh_token = (
            user_tokens.get("refresh_token")
            or settings.GOOGLE_REFRESH_TOKEN
            or None
        )
        access_token = user_tokens.get("access_token") or None

        if not refresh_token:
            return {"message_id": None, "status": "failed",
                    "error": "No refresh token available. Connect Gmail in Settings."}

        from google.auth.exceptions import RefreshError

        # Always build Credentials without a stale access_token so the library
        # is forced to do a clean refresh via the refresh_token.
        creds = Credentials(
            token=None,  # don't reuse a potentially stale access_token
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        # Refresh to get a fresh access token before making any API call.
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            err_str = str(exc)
            logger.warning("gmail_token_refresh_failed", error=err_str)
            if "invalid_grant" in err_str.lower() or "token has been expired" in err_str.lower():
                return {
                    "message_id": None,
                    "status": "failed",
                    "error": err_str,
                    "error_code": "token_revoked",
                }
            # Other RefreshError (network, config) — surface as-is
            return {"message_id": None, "status": "failed", "error": err_str}

        service = build("gmail", "v1", credentials=creds)

        # Build email message — prefer in-memory bytes, fall back to file path
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain"))
        if attachment_bytes:
            part = MIMEApplication(attachment_bytes, _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=attachment_filename)
            msg.attach(part)
        elif attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment",
                                filename=os.path.basename(attachment_path))
                msg.attach(part)

        msg["to"] = to_email
        msg["subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        logger.info("gmail_sent", message_id=result.get("id"), to=to_email)
        return {"message_id": result.get("id"), "status": "sent"}

    except Exception as e:
        err_str = str(e)
        # Catch any invalid_grant that slipped past the RefreshError handler
        if "invalid_grant" in err_str.lower() or "token has been expired" in err_str.lower():
            logger.warning("gmail_token_revoked", error=err_str)
            return {
                "message_id": None,
                "status": "failed",
                "error": err_str,
                "error_code": "token_revoked",
            }
        logger.error("gmail_send_error", error=err_str, exc_info=True)
        return {"message_id": None, "status": "failed", "error": err_str}

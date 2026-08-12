import logging
import smtplib
from dataclasses import asdict, dataclass
from email.message import EmailMessage as SMTPMessage
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("forgeops.email")
development_outbox: list["EmailMessage"] = []


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    text_body: str
    html_body: str | None = None
    template: str = "generic"


class EmailService(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class DevelopmentEmailService:
    def send(self, message: EmailMessage) -> None:
        development_outbox.append(message)
        logger.info(
            "development_email_captured",
            extra={"event": "development_email", "template": message.template},
        )


class SMTPEmailService:
    def send(self, message: EmailMessage) -> None:
        smtp_message = SMTPMessage()
        smtp_message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
        smtp_message["To"] = message.recipient
        smtp_message["Subject"] = message.subject
        smtp_message.set_content(message.text_body)
        if message.html_body:
            smtp_message.add_alternative(message.html_body, subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            if settings.smtp_use_tls:
                client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password or "")
            client.send_message(smtp_message)


def get_email_service() -> EmailService:
    return SMTPEmailService() if settings.email_backend == "smtp" else DevelopmentEmailService()


def message_to_payload(message: EmailMessage) -> dict:
    return asdict(message)


def message_from_payload(payload: dict) -> EmailMessage:
    return EmailMessage(
        recipient=str(payload["recipient"]),
        subject=str(payload["subject"]),
        text_body=str(payload["text_body"]),
        html_body=str(payload["html_body"]) if payload.get("html_body") else None,
        template=str(payload.get("template", "generic")),
    )

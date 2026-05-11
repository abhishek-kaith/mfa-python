"""Render and send transactional emails."""

from __future__ import annotations

from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def send_template_email(
    *,
    to: str,
    subject: str,
    template: str,
    context: dict | None = None,
) -> None:
    """Render a plain-text template and send it.

    The template should live under ``templates/emails/`` and produce text
    suitable for a plain-text email body.
    """
    body = render_to_string(template, context or {})
    msg = EmailMessage(subject=subject, body=body, to=[to])
    msg.send(fail_silently=False)

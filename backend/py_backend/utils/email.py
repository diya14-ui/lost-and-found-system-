import smtplib
from email.message import EmailMessage
from typing import Optional
from py_backend.config import Config


def send_email(to_address: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email using configured SMTP settings. Returns True on success, False otherwise."""

    host = Config.SMTP_HOST
    if not host:
        return False

    port = Config.SMTP_PORT
    user = Config.SMTP_USER
    password = Config.SMTP_PASSWORD
    from_addr = Config.SMTP_FROM
    use_tls = Config.SMTP_USE_TLS

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address
    if text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(html_body, subtype="html")

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
        server.ehlo()
        if use_tls and port != 465:
            server.starttls()
            server.ehlo()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False

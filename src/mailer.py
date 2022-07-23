import os
import smtplib
import ssl
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import config


def send(msg_body: str, msg_attachment_path: str = None):
    ctx = ssl.create_default_context()
    receivers = config.RECEIVER_EMAIL_ADDRESSES.split(",")

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Third Eye alert - {str(datetime.now())}"
    message["From"] = config.EMAIL_SENDER_ADDRESS
    message["To"] = ", ".join(receivers)

    if msg_attachment_path:
        with open(msg_attachment_path, "rb") as f:
            file = MIMEApplication(f.read())
        disposition = f"attachment; filename={os.path.basename(msg_attachment_path)}"
        file.add_header("Content-Disposition", disposition)
        message.attach(file)

    html = f"""
    <html>
      <body>
        <p>Hey there,<br>
           {msg_body}
        </p>
      </body>
    </html>
    """

    message.attach(MIMEText(msg_body, "plain"))
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", port=465, context=ctx) as server:
        try:
            server.login(config.EMAIL_SENDER_ADDRESS, config.EMAIL_SENDER_PASSWORD)
            server.sendmail(config.EMAIL_SENDER_ADDRESS, receivers, message.as_string())
            logging.info(f'Email sent to {receivers}.')
        except Exception as e:
            logging.error(f'Email error: {str(e)}')

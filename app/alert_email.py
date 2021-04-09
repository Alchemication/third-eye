# Web link: https://realpython.com/python-send-email/

import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


smtp_server = "smtp.gmail.com"
port = 587  # For TLS
sender_email = "1234@gmail.com"
receiver_emails = ["123@gmail.com"]
password = ''

message = MIMEMultipart("alternative")
message["Subject"] = "multipart test"

# Create the plain-text and HTML version of your message
text = """
Hi,
How are you?
Real Python has many great tutorials:
www.realpython.com
"""

html = """
<html>
  <body>
    <p>Hi,<br>
       How are you?<br>
       <a href="http://www.realpython.com">Real Python</a> 
       has many great tutorials.
    </p>
  </body>
</html>
"""

# Turn these into plain/html MIMEText objects
part1 = MIMEText(text, "plain")  # this will be displayed on Apple Watch (for example)
part2 = MIMEText(html, "html")  # this will be displayed in most of email clients

# Add HTML/plain-text parts to MIMEMultipart message
# The email client will try to render the last part first
message.attach(part1)
message.attach(part2)

# Encode file in ASCII characters to send by email

filepath = '/home/pi/Laboratory/video-stream-api/app/images'
filename = '205615.023453.jpg'

# Open file in binary mode
with open(f'{filepath}/{filename}', "rb") as attachment:
    # Add file as application/octet-stream
    # Email client can usually download this automatically as attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())

encoders.encode_base64(part)

# Add header as key/value pair to attachment part
part.add_header(
    "Content-Disposition",
    f"attachment; filename= {filename}",
)

# Add attachment to message
message.attach(part)

# Log in to server using secure context and send email
context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(
        sender_email, receiver_emails, message.as_string()
    )
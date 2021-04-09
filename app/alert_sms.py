import os
from twilio.rest import Client

twilio_phone_no = ''
my_phone_numbers = ''.split(',')
account_sid = ''
auth_token = ''

# Your Account Sid and Auth Token from twilio.com/console
# and set the environment variables. See http://twil.io/secure
#account_sid = os.environ['TWILIO_ACCOUNT_SID']
#auth_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(account_sid, auth_token)

for p in my_phone_numbers:
    message = client.messages \
                    .create(
                         body="Join Earth's mightiest heroes. Like Kevin Bacon.",
                         from_=twilio_phone_no,
                         media_url=['https://demo.twilio.com/owl.png'],
                         to=p
                     )
    print(message.status)

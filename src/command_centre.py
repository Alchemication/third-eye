# usage: python command_centre.py

import email_listener
import config
from models import StreamConnection
import logging
from datetime import datetime, timedelta
from database import Session
import json
import threading
import re
from pyngrok import ngrok
from twilio.rest import Client
from time import sleep


def get_last_stream_conn() -> StreamConnection:
    """Get last inserted StreamConnection"""
    return Session.query(StreamConnection).order_by(StreamConnection.id.desc()).first()


def get_open_stream_url():
    """
    Return URL of currently opened stream,
    or None if no streams are currently open#
    """
    sc = get_last_stream_conn()
    # return None if current timestamp is greater than the expiry ts
    now = datetime.now()
    if now > sc.expiration_ts:
        return None
    # otherwise, return stream URL
    return sc.temp_backend_url


def create_listener():
    """
    Create new listener, which will listen for new emails.
    Currently Google must be throttling request on custom iMap connections,
    as it tends to take ~20 seconds to receive a new email after it's sent.
    Bastards!
    TODO: Find a way to process emails instantly without a delay!
    """

    # Set your email, password, what folder you want to listen to, and where to save attachments
    el = email_listener.EmailListener(config.EMAIL_SENDER_ADDRESS, config.EMAIL_SENDER_PASSWORD, "Inbox", "./tmp")

    # Log into the IMAP server
    el.login()

    # Get the emails currently unread in the inbox
    messages = el.scrape()
    if len(messages):
        logger.info(f'There are currently {len(messages)} message(s) unread in the'
                    f' Inbox and will be ignored')

    # Start listening to the inbox and timeout after some time
    timeout = 180  # 3 hrs
    logger.info(f'Listening for emails...')
    el.listen(timeout, process_func=process_email)


def process_command(sender_phone_no: str, cmd: str = 'Eye-OpenStream') -> None:
    """Process system commands"""

    # check command name
    if cmd == 'Eye-OpenStream':
        # TODO: if connection is already open, send sms with URL & return early

        # open up backend connection
        ngrok_tunnel_backend = ngrok.connect(8000, bind_tls=True)
        logging.info(f'Tunnelling backend at : {ngrok_tunnel_backend.public_url}')

        # create StreamConnection entry in the DB,
        # so frontend app can use the backend video feed URL
        now = datetime.now()
        expiry_ts = now + timedelta(minutes=int(config.STREAM_EXPIRY_SEC / 60))
        sc = StreamConnection(create_ts=now,
                              expiration_ts=expiry_ts,
                              requester_phone_no=sender_phone_no,
                              temp_backend_url=ngrok_tunnel_backend.public_url)
        Session.add(sc)
        Session.commit()

        # open up frontend connection, grab public URL
        ngrok_tunnel_frontend = ngrok.connect(8001, bind_tls=True)
        logging.info(f'Tunnelling frontend at : {ngrok_tunnel_frontend.public_url}')

        # update StreamConnection in the DB with public URL
        sc = get_last_stream_conn()
        sc.temp_frontend_url = ngrok_tunnel_frontend.public_url
        Session.add(sc)
        Session.commit()

        # send link to frontend to the user via SMS
        logging.info('Sending SMS Notification')
        msg_body = f'Third Eye Live Stream is available here: {ngrok_tunnel_frontend.public_url} and' \
                   f' will expire in {int(config.STREAM_EXPIRY_SEC / 60)} minutes (at {str(expiry_ts)[:19]}).'
        try:
            client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)
            message = client.messages.create(body=msg_body, from_=config.TWILIO_PHONE_NUMBER,
                                             to=sender_phone_no)
            sms_msg_sid = message.sid
            logging.info(f'Message sent to Twilio, message id: {sms_msg_sid}')
        except Exception as e:
            logging.error(f'SMS error: {str(e)}')

        # wait for N-seconds
        logging.info(f'Keeping stream open for {config.STREAM_EXPIRY_SEC} seconds')
        sleep(config.STREAM_EXPIRY_SEC)

        # close nkgrok connections
        logging.info(f'Closing tunnels')
        ngrok.disconnect(ngrok_tunnel_frontend.public_url)
        ngrok.disconnect(ngrok_tunnel_backend.public_url)

        return
    raise ValueError('Only Eye-OpenStream command is available')


def process_email(*args):
    """
    When new email arrives, validate the content and execute the command.
    Email data required:
    - Subject - command to execute (currently only supported is Eye-OpenStream)
    - Email sender - must be in the list of users defined in config (env variable)
    - Email attachment - must contain a valid JSON file with following keys:
        - ApiKey (must match value defined in config / env variable)
        - PhoneNumber (must be in the list of allowed numbers in the config)
    """

    logger.info('New email arrived')

    for mail_sender, mail_data in args[1].items():

        logger.info(f'Mail Sender: {mail_sender}')
        exec_cmd = mail_data["Subject"]
        logger.info(f'Mail Subject/Command to execute: {exec_cmd}')

        # check if attachment is present
        if 'attachments' not in mail_data or len(mail_data['attachments']) == 0:
            logger.warning('No attachments found. Email ignored')
            continue

        # parse attachment (it should be a json file)
        with open(mail_data['attachments'][0], 'r') as fp:
            try:
                instructions = json.load(fp)
            except Exception as e:
                logger.warning(f'Could not parse attachment into dict. Error: {str(e)}')
                continue

        # display instructions
        logger.info(f'Instructions: {str(instructions)}')

        # validate API Key
        if 'ApiKey' not in instructions or instructions['ApiKey'] != config.STREAM_API_KEY:
            logger.warning(f'API Key missing or incorrect API Key provided')
            continue

        # tidy up email address (will be in an ID_emailAddress format)
        mail_sender = "_".join(mail_sender.split('_')[1:])

        # check if sender is in the whitelist
        if mail_sender not in config.RECEIVER_EMAIL_ADDRESSES:
            logger.warning(f'Mail sender not recognized ({mail_sender})')
            continue

        # verify if phone address is present
        if 'PhoneNumber' not in instructions:
            logger.warning(f"Phone number not present")
            continue

        # tidy up phone number (will contain spaces and parens)
        phone_no = re.sub(r'[() ]', '', instructions['PhoneNumber'])

        # verify if phone address is in the whitelist
        if phone_no not in config.NOTIFY_PHONE_NUMBERS:
            logger.warning(f"Phone number not recognized ({phone_no})")
            continue

        # process command in a separate thread
        t = threading.Thread(target=process_command, args=(phone_no,))
        t.daemon = True
        t.start()


if __name__ == '__main__':
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt=config.LOGGING_DATE_FORMAT)
    logger = logging.getLogger()

    create_listener()

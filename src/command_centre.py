# usage: python command_centre.py

import email_listener
import config
from models import Command
import logging
from datetime import datetime
from database import Session


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
    logger.info(f'There are currently {len(messages)} message(s) unread in the Inbox. These will be ignored')

    # Start listening to the inbox and timeout after some time
    timeout = 180  # 3 hrs
    el.listen(timeout, process_func=process_email)


def process_command(cmd: Command):
    """Process system commands"""
    if cmd.command_type == 'email' and cmd.command == 'open stream':
        pass
    if cmd.command_type == 'email' and cmd.command == 'start alerts':
        pass
    if cmd.command_type == 'email' and cmd.command == 'pause alerts':
        pass
    if cmd.command_type == 'email' and cmd.command == 'open stream':
        pass
    raise ValueError('This command type and command are not supported')


def process_email(*args):
    """When new email arrives, validate, save and execute a command"""

    logger.info('New email arrived')

    for key, value in args[1].items():
        mail_sender = key
        mail_data = value
        logger.info(f'Sender: {mail_sender}')
        logger.info(f'Subject: {mail_data["Subject"]}')
        logger.info(f'Body: {mail_data["Plain_Text"]}')
        logger.info('Creating command and saving...')
        cmd = Command(create_ts=datetime.now(), command_type='email', command=mail_data["Subject"],
                      raw_body=mail_data["Plain_Text"])
        # TODO: validate email data before saving in the DB, perhaps enforce sth like an API Key inside
        Session.add(cmd)
        Session.commit()

        # execute command
        # TODO: this might have to be executed in a separate thread
        logger.info('Process command...')
        process_command(cmd)


if __name__ == '__main__':
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt="%H:%M:%S")
    logger = logging.getLogger()

    create_listener()

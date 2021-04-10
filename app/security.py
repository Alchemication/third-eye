from datetime import datetime, timedelta
from typing import List
import pandas as pd
import config
import logging
import cv2
import numpy as np
from models import ObjectDetection, Alert, HomeOccupancy
from database import engine, Session
from os import path, mkdir
from twilio.rest import Client
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def find_owners_at_home(db_conn) -> list:
    """Check if home owner device was detected in the last N-minutes"""

    # TODO: Consider removing this function and use ORM instead for consistency in the app

    # calculate curr time - N minutes
    min_occupancy_time = str(datetime.now() - timedelta(minutes=config.OWNERS_OUTSIDE_HOME_MIN))

    # fetch results from DB
    df = pd.read_sql(f"""
        SELECT found_owners
        FROM home_occupancy
        WHERE occupancy_status = 'home'
            AND update_ts >= :min_occupancy_time
        ORDER BY update_ts DESC
        LIMIT 1
    """, params={'min_occupancy_time': min_occupancy_time}, con=db_conn)
    return df['found_owners'].values.tolist()


def find_owners_at_home_orm() -> list:
    """
    Check if registered devices were detected on the Network in the last N-minutes.
    This is a more orm-friendly alternative to find_owners_at_home.
    """

    # calculate curr time - N minutes
    min_occupancy_time = str(datetime.now() - timedelta(minutes=config.OWNERS_OUTSIDE_HOME_MIN))
    # find last entry which matches "home" status
    devices_at_home = (Session
                       .query(HomeOccupancy)
                       .filter(HomeOccupancy.occupancy_status == 'home', HomeOccupancy.update_ts >= min_occupancy_time)
                       .order_by(HomeOccupancy.update_ts.desc())
                       .first())
    # if entry is not found - return empty list
    if devices_at_home is None:
        return []
    # otherwise, return a list of device owners
    return devices_at_home.found_owners


def fetch_last_alert() -> Alert:
    """Get last alert triggered by the system"""
    return (Session
            .query(Alert)
            .order_by(Alert.create_ts.desc())
            .first())


def check_alerts(detections: List[ObjectDetection], curr_frame: np.array) -> bool:
    """Check if an alert needs to be triggered"""
    logging.info(f'Security CheckAlerts running...')

    # check if we are in the OVERRIDE hours,
    # these will say, that no-matter if house is occupied,
    # an alert will be triggered
    now = datetime.now()
    override_on = False
    if config.SECURITY_ON_OVERRIDE_HOURS is not None:
        for hr_rg in config.SECURITY_ON_OVERRIDE_HOURS:
            if is_hr_between(now.hour, hr_rg):
                logging.info(f'Alert override ON. Curr hr. ({now.hour}) is within override range {str(hr_rg)}')
                override_on = True
                break

    # check if house is occupied (if the OVERRIDE above is not ON right now)
    home_occupied = False
    if not override_on:
        # finally, if we still have potential intruders available,
        # we can check if home owners are away, and only then trigger an alert,
        # this check is left to the end as it's the slowest part (DB query)
        home_owners = find_owners_at_home_orm()
        if home_owners is not None and len(home_owners) > 0:
            home_occupied = True
            logging.info(f'Alert skipped. Owners are at home for at'
                         f' least {config.OWNERS_OUTSIDE_HOME_MIN} minute(s)')
            return False

    # trigger alert if OVERRIDE is ON or house is not occupied
    if override_on or not home_occupied:
        # at this stage, we can trigger an alert to home owners as we do have a
        # potential intruder in the security zone area and home owners are away
        extra_text = 'alert override is ON' if override_on else 'house is not occupied'
        logging.info(f'Trigger alert. Potential intruder(s) detected and {extra_text}')

        # create folder for current date if does not exist yet
        date_folder = f'{config.IMG_FOLDER}/{str(now.date())}'
        if not path.exists(date_folder):
            mkdir(date_folder)
        # save image in the images folder
        img_name = f"{str(now)[11:].replace(':', '')}.jpg"  # '203732.507061.jpg'
        cv2.imwrite(f'{date_folder}/{img_name}', curr_frame)
        logging.info(f'File {date_folder}/{img_name} saved')

        # check if enough time has elapsed since last notification,
        # for this, fetch the metadata for the last alert
        last_alert = fetch_last_alert()
        # calculate the time between now and -N seconds (set in config)
        alert_check_time = now - timedelta(seconds=config.MIN_SEC_BETWEEN_ALERTS)
        # if alert has been triggered recently, skip the next one
        if last_alert.create_ts >= alert_check_time:
            logging.info(f'Alert already triggered at {str(last_alert.create_ts)}')
            return False
        # trigger alert
        logging.info(f'Last alert sent at {str(last_alert.create_ts)}. Trigger alert')
        intruders, msg_id, mail_resp = trigger_alert(detections, date_folder, img_name)
        # register new alert in the DB
        a = Alert(create_ts=now, title='Potential intruders detected', alert_metadata={
            'intruders': intruders,
            'msg_id': msg_id,
            'mail_resp': mail_resp,
            'img_path': f'{date_folder}/{img_name}',
            'prev_alert': str(last_alert.create_ts),
            'checked_intruder_objects': config.INTRUDER_OBJECTS
        })
        Session.add(a)
        Session.commit()
        # return True, which indicates alert triggered
        return True

    # returning False indicates no alerts, code should not even get here
    logging.info('Alert not triggered. Final check completed')
    return False


def trigger_alert(detections: List[ObjectDetection], img_folder: str, filename: str) -> tuple:
    """
    Send an email or/and sms notification to home owners
    Returns a list of identified labels, sms ID (or None if disabled)
    and email response data (or None if disabled)
    """

    # compose message body
    intruder_labels = [i.label for i in detections]
    msg_body = f'Third Eye registered potential silent intruders: {", ".join(intruder_labels)}.'

    # send sms
    sms_msg_sid = None
    if config.SMS_NOTIFICATIONS_ENABLED:
        logging.info('Sending SMS Notification')
        try:
            client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)
            for p in config.NOTIFY_PHONE_NUMBERS:
                message = client.messages.create(body=msg_body, from_=config.TWILIO_PHONE_NUMBER, to=p)
                sms_msg_sid = message.sid
                logging.info(f'Message sent to Twilio, message id: {sms_msg_sid}')
        except Exception as e:
            logging.error(f'SMS error: {str(e)}')

    # send email
    email_resp = None
    if config.EMAIL_NOTIFICATIONS_ENABLED:
        logging.info('Sending Email Notification')
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Third Eye alert - {str(datetime.now())}"

        # Create the plain-text and HTML version of the message
        plain_text = msg_body
        html = f"""
        <html>
          <body>
            <p>Hey there,<br>
               {msg_body}
            </p>
          </body>
        </html>
        """

        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(plain_text, "plain")  # this will be displayed on Apple Watch (for example)
        part2 = MIMEText(html, "html")  # this will be displayed in most of email clients

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)

        # Open file in binary mode
        with open(f'{img_folder}/{filename}', "rb") as attachment:
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
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(config.EMAIL_SENDER_ADDRESS, config.EMAIL_SENDER_PASSWORD)
                email_resp = server.sendmail(config.EMAIL_SENDER_ADDRESS, config.RECEIVER_EMAIL_ADDRESSES,
                                            message.as_string())
                logging.info(f'Email sent. Server response: {str(email_resp)}')
        except Exception as e:
            logging.error(f'Email error: {str(e)}')

        # return all elements
        return intruder_labels, sms_msg_sid, email_resp


def is_hr_between(time: int, time_range: tuple) -> bool:
    """
    Calculate if hour is within a range of hours
    Example: is_hr_between(4, (24, 5)) will match hours from 24:00:00 to 04:59:59
    """
    if time_range[1] < time_range[0]:
        return time >= time_range[0] or time <= time_range[1]
    return time_range[0] <= time <= time_range[1]

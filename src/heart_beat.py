# Set up a Message Queue server, which will receive images
# every N-minutes, and heart beat signals every N-seconds.
# Images will be stored on SD Card for forensics.
# Heart beats will be used to determine if camera stream is alive (it may
# need to be restarted on some camera models).
# Log and notify admin when camera needs to be restarted.
import imagezmq
import cv2
import traceback
import sys
import logging

import subprocess

import config
import time
import threading
from models import HeartBeat
from datetime import datetime, timedelta
from database import Session
from twilio.rest import Client


def is_healthy(heart_beat: HeartBeat) -> bool:
    """
    Generate status based on if the heart beat occurred within
    last N-seconds, as per config setting.
    If True is returned, then heart beat is ok, otherwise video stream
    has been in idle mode for too long.
    """
    max_age = datetime.now() - timedelta(seconds=config.HEART_BEAT_INTERVAL_MAX_IDLE_N_SEC)
    return heart_beat.create_ts >= max_age


def fetch_last_heart_beat() -> HeartBeat:
    """Get last HeartBeat recorded in the DB"""
    return (Session
            .query(HeartBeat)
            .order_by(HeartBeat.create_ts.desc())
            .first())


def hear_beat_monitor():
    """
    Keep checking heart beats every N-seconds.
    If heart beat is not detected in N-seconds,
    restart video capture process
    """
    while True:
        logging.debug('Checking heart beat')

        # grab last heart beat from the DB
        last_heart_beat = fetch_last_heart_beat()

        # determine if last heart beat occurred within specified time
        heart_beat_status = is_healthy(last_heart_beat)

        # if heart beat is ok - wait for some time interval and continue
        if heart_beat_status:
            time.sleep(30)
            continue

        # send text alert to admin
        logging.info('Sending SMS Notification')
        try:
            msg_body = f'Third Eye noticed a problem with the video stream. Backend process will be restarted'
            client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)
            for p in config.NOTIFY_PHONE_NUMBERS:
                message = client.messages.create(body=msg_body, from_=config.TWILIO_PHONE_NUMBER, to=p)
                sms_msg_sid = message.sid
                logging.info(f'Message sent to Twilio, message id: {sms_msg_sid}')
        except Exception as e:
            logging.error(f'SMS error: {str(e)}')

        # restart backend process
        # construct command
        CMD = f'/usr/bin/sudo /usr/bin/supervisorctl restart third-eye-backend'
        logging.info(f'Executing cmd: {CMD}')

        # execute CLI process
        p = subprocess.Popen(CMD.split(' '), stdout=subprocess.PIPE)
        out, err = p.communicate()
        logging.info(str(out))

        # wait another 30 sec before going into next iteration
        logging.info('Pausing for a moment, so backend can restart')
        time.sleep(30)


def main():
    """Collect messages from the message queue and save heart beats in the DB"""
    try:
        logging.info(f'Starting MQ server on {config.HEART_BEAT_SUB_URL}')
        with imagezmq.ImageHub(open_port=config.HEART_BEAT_SUB_URL, REQ_REP=False) as image_hub:
            logging.info(f'Ready to collect messages')
            while True:  # receive images until Ctrl-C is pressed
                dev_name, image = image_hub.recv_image()
                logging.debug(f'Heart beat received from {dev_name} with image shape {image.shape}')
                # save heart beat in the DB
                hb = HeartBeat(create_ts=datetime.now(), im_filename='N/A')
                Session.add(hb)
                Session.commit()
                # TODO: save file on the hard drive
    except (KeyboardInterrupt, SystemExit):
        pass  # Ctrl-C was pressed to end program
    except Exception as e:
        logging.error(f'Python error with no Exception handler: {str(e)}')
        logging.error(str(traceback.print_exc()))
    finally:
        sys.exit()


if __name__ == '__main__':
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt=config.LOGGING_DATE_FORMAT)
    logger = logging.getLogger()
    # kick off hear_beat_monitor in a separate thread
    t = threading.Thread(target=hear_beat_monitor)
    t.daemon = True
    t.start()

    # kick off main message subscriber in the main thread
    main()

# Set up a Message Queue server, which will receive images
# every N-minutes, and heart beat signals every N-seconds.
# New images will be stored on SD Card for forensics, and old images deleted to remove clutter/save space
# Heart beats will be used to determine if camera stream is alive (it may
# need to be restarted on some camera models).
# Log and notify admin when camera needs to be restarted.

# Usage: python heart_beat.py

import os
import pandas as pd
import imagezmq
import cv2
import traceback
import sys
import logging
from os import path, mkdir
import subprocess
import config
import time
import threading
from models import HeartBeat
from datetime import datetime, timedelta
from database import Session


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
    Keep running a heart beat every N-seconds:
    - Check if images need to be archived
    - If heart beat is not detected in N-seconds, restart video capture process
    """
    SLEEP_TIME = 30
    prev_day = None
    while True:
        logging.debug('Heart beat triggered')

        # ====================================
        # === Delete old heart beat images ===
        # ====================================

        curr_day = datetime.now().day
        if curr_day != prev_day:
            logging.info('Check for old heart-beat image candidates for deletion')

            # find all folders with images
            all_im_folders = os.listdir(config.IMG_FOLDER)

            # calculate dates to keep based on configuration
            now = datetime.now()
            min_date = now - timedelta(days=config.USE_HISTORICAL_DAYS)
            keep_dates = [str(dt.date()) for dt in pd.date_range(min_date, now)]

            # figure out candidates for image deletion
            del_dirs = [dt for dt in all_im_folders if dt not in keep_dates]

            # walk through old directories and remove heart beat images
            for dt in del_dirs:
                logging.info(f'Checking folder for old heart beat images: {dt}')
                dt_dir = f'{config.IMG_FOLDER}/{dt}'
                for f in [f for f in os.listdir(dt_dir) if config.HEART_BEAT_FILES_IDENTIFIER in f]:
                    logging.info(f'Delete file: {f}')
                    os.unlink(f'{dt_dir}/{f}')

            # set prev day to curr day
            prev_day = curr_day

        # ==================================
        # === Detect frozen video stream ===
        # ==================================
        # grab last heart beat from the DB
        last_heart_beat = fetch_last_heart_beat()

        # determine if last heart beat occurred within specified time
        heart_beat_status = is_healthy(last_heart_beat)

        # if heart beat is not healthy - restart backend process
        if not heart_beat_status:
            # construct command
            CMD = f'/usr/bin/sudo /usr/bin/supervisorctl restart third-eye-backend'
            logging.info(f'Video stalled, restarting backend: {CMD}')

            # execute CLI process
            p = subprocess.Popen(CMD.split(' '), stdout=subprocess.PIPE)
            out, err = p.communicate()
            logging.info(str(out))

        # wait for a while before going into next iteration
        logging.debug(f'Waiting for {SLEEP_TIME} seconds')
        time.sleep(SLEEP_TIME)


def main():
    """Collect messages from the message queue and save heart beats in the DB"""
    try:
        logging.info(f'Starting MQ server on {config.HEART_BEAT_SUB_URL}')
        with imagezmq.ImageHub(open_port=config.HEART_BEAT_SUB_URL, REQ_REP=False) as image_hub:
            logging.info(f'Ready to collect messages')
            # keep track of current minute, as files will be saved once per minute
            prev_min = None
            while True:  # receive images until Ctrl-C is pressed
                dev_name, image = image_hub.recv_image()
                # logging.debug(f'Heart beat received from {dev_name} with image shape {image.shape}')
                # get current date/time
                now = datetime.now()
                # make sure we only save 1 file per minute (to save some space on the Pi)
                curr_min = now.minute
                if curr_min != prev_min:
                    date_folder = f'{config.IMG_FOLDER}/{str(now.date())}'
                    if not path.exists(date_folder):
                        mkdir(date_folder)
                    # save image in the images folder on each new minute
                    img_name = f"{str(now)[11:].replace(':', '')}_{config.HEART_BEAT_FILES_IDENTIFIER}.jpg"
                    cv2.imwrite(f'{date_folder}/{img_name}', image)
                    logging.info(f'Saving Heart-Beat file: {date_folder}/{img_name}')
                    prev_min = curr_min
                # save heart beat in the DB
                hb = HeartBeat(create_ts=datetime.now(), im_filename=f'{date_folder}/{img_name}')
                Session.add(hb)
                Session.commit()
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

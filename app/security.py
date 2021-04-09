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


def find_owners_at_home(db_conn) -> list:
    """Check if home owner device was detected in the last N-minutes"""

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
    TODO: Consider removing function above
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
    return devices_at_home['found_owners']


def fetch_last_alert() -> Alert:
    """Get last alert triggered by the system"""
    return (Session
            .query(Alert)
            .order_by(Alert.create_ts.desc())
            .first())


def check_alerts(detections: List[ObjectDetection], curr_frame: np.array) -> bool:
    """
    - Check if current hour ignores fact if home is occupied
        - Check if home owners are away
    If all the conditions are met - trigger an alert
    If alert is triggered - return True, otherwise return False
    """
    logging.info(f'Security CheckAlerts running...')

    # check if an option to trigger alerts during predefined time is ON
    now = datetime.now()
    override_on = False
    if config.SECURITY_ON_OVERRIDE_HOURS is not None:
        for hr_rg in config.SECURITY_ON_OVERRIDE_HOURS:
            if is_hr_between(now.hour, hr_rg):
                logging.info(f'Current hour ({now.hour}) is within override range {str(hr_rg)}')
                override_on = True
                break

    # if we do have an override ON, then next step is redundant
    home_occupied = False
    if not override_on:
        # finally, if we still have potential intruders available,
        # we can check if home owners are away, and only then trigger an alert,
        # this check is left to the end as it's the slowest part (DB query)
        home_owners = find_owners_at_home_orm()
        if home_owners is not None and len(home_owners) > 0:
            home_occupied = True
            logging.info(f'Alert not triggered. Owners are at home for at'
                         f' least {config.OWNERS_OUTSIDE_HOME_MIN} minute(s)')
            return False

    # check if override is ON or house is not occupied
    if override_on or not home_occupied:
        # at this stage, we can trigger an alert to home owners as we do have a
        # potential intruder in the security zone area and home owners are away
        logging.info('Trigger alert. Potential intruder detected and owners are not at home')

        # create folder for current date if does not exist yet
        date_folder = f'{config.IMG_FOLDER}/{str(now.date())}'
        if not path.exists(date_folder):
            mkdir(date_folder)
        # save image in the images folder
        img_name = f"{str(datetime.now())[11:].replace(':', '')}.jpg"  # '203732.507061.jpg'
        cv2.imwrite(f'{date_folder}/{img_name}', curr_frame)
        logging.info(f'File {date_folder}/{img_name} saved')

        # check if notification needs to be sent to home owners
        # this will happen only N-seconds from the last alert,
        # this is a 3-step process:
        # - first, fetch the last alert from the DB
        last_alert = fetch_last_alert()
        # - calculate the time between now and -N seconds (set in config)
        alert_check_time = datetime.now() - timedelta(seconds=config.MIN_SEC_BETWEEN_ALERTS)
        # - if alert has been triggered recently, skip the next one
        if last_alert.create_ts >= alert_check_time:
            logging.info(f'Alert already triggered at {str(last_alert.create_ts)}')
            return False

        logging.info(f'Last alert sent at {str(last_alert.create_ts)}. Trigger a new alert')
        return True

    # returning False indicates no alerts, code should not even get here
    logging.info('Alert not triggered. Final check completed')
    return False


def is_hr_between(time: int, time_range: tuple) -> bool:
    """
    Calculate if hour is within a range of hours
    Example: is_hr_between(4, (24, 5)) will match hours from 24:00:00 to 04:59:59
    """
    if time_range[1] < time_range[0]:
        return time >= time_range[0] or time <= time_range[1]
    return time_range[0] <= time <= time_range[1]

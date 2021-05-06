import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import USE_HISTORICAL_DAYS, TRACK_OBJECTS, OBJ_PROBA
import argparse
from database import Session
from models import MotionDetection, ObjectDetection
import logging
import config
from tqdm import tqdm


def gen_dts(size: int) -> tuple:
    """
    Generate normally distributed random dates for the observations,
    param size drives the number of dates per day, how many days is pulled
    from the config (USE_HISTORICAL_DAYS)
    """

    # generate dt objects for today and today minus N-days
    today = datetime.now()
    historical_day = datetime.now() - timedelta(days=USE_HISTORICAL_DAYS)

    # generate randomized dataset
    generated = []
    counter = 0
    dt_range = pd.date_range(historical_day.date(), today.date(), freq='D')
    for dt in tqdm(dt_range):
        curr_dt = []
        # activities often occur mostly during the day and
        # evening, so normal distribution with a peak at 15:00
        # and large scale is a good fit, also makes sense to clip the
        # values in case of outliers (we have only 24 hours in a day on Earth;)
        rand_hrs = np.clip(np.random.normal(15, scale=2.4, size=size).astype(int), 5, 21)
        for hr in rand_hrs:
            # minutes and seconds can be totally random
            rand_min, rand_sec = str(np.random.randint(0, 60)).zfill(2), str(np.random.randint(0, 60)).zfill(2)
            curr_dt.append(datetime.strptime(f'{dt.date()} {hr}:{rand_min}:{rand_sec}', '%Y-%m-%d %H:%M:%S'))
            counter += 1
        generated.append({'dt': dt, 'values': curr_dt})
    return generated, counter


def populate(dts: list, db_table: str) -> int:
    """Populate DB table with random observations"""

    counter = 0

    for dt_data in tqdm(dts):
        for i, dt in enumerate(dt_data['values']):
            if db_table == 'motion_detections':
                # create motion detection model
                ob = MotionDetection(create_ts=dt, x=0, y=0, w=100, h=100, area=100)
            elif db_table == 'object_detections':
                rand_label = np.random.choice(TRACK_OBJECTS, p=OBJ_PROBA)  # pick label with weighted probability
                # assign higher object ID to more frequent objects
                rand_mean = 10 if rand_label in ['car', 'person', 'truck'] else 2
                # choose a single number from Normal with the mean driven by label type
                rand_obj_id = int(np.max([0, np.random.normal(rand_mean, scale=2.0, size=1).astype(int)[0]]))
                # create object detection model
                ob = ObjectDetection(create_ts=dt, x=0, y=0, w=100, h=100, area=100, obj_id=rand_obj_id,
                                     label=rand_label)
            else:
                raise ValueError(f'Table {db_table} does not exist')
            try:
                Session.add(ob)
                Session.commit()
                counter += 1
            except Exception as e:
                logging.error(f'Detection not saved: {str(e)}')
    return counter


if __name__ == '__main__':
    # set up logger
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt=config.LOGGING_DATE_FORMAT)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description='Sample data generator')
    parser.add_argument('--table', type=str, help='name of table to populate', required=True)
    parser.add_argument('--size', type=int, help='how many observations to generate in a single day', required=True)
    args = parser.parse_args()

    logging.info('Generating date-times')
    dts, counter = gen_dts(args.size)
    logging.info(f'Generated {counter} date-times')
    logging.info('Populating DB table')
    counter = populate(dts, args.table)
    logging.info(f'Inserted {counter} records')

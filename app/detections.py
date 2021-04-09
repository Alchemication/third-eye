from models import MotionDetection, ObjectDetection
import config
import pandas as pd
from datetime import datetime
import logging
from edgetpu.detection.engine import DetectionEngine
from database import Session


def get_obj_det_comps(model_file: str, labels_file: str) -> tuple:
    """Load object detection model file and labels"""
    logging.info("Loading Edge TPU object detection model and labels")
    model = DetectionEngine(model_file)
    labels = {}
    # loop over the class labels file
    for row in open(labels_file):
        # unpack the row and update the labels dictionary
        (classID, curr_label) = row.strip().split(maxsplit=1)
        labels[int(classID)] = curr_label.strip()
    return model, labels


def save_detections(detections: list) -> None:
    """Save detections into DB"""
    logging.info(f'Saving {len(detections)} detection(s)')
    try:
        # stage detections for DB insert
        Session.add_all(detections)
        # flush inserts into DB
        Session.commit()
    except Exception as e:
        logging.error(f'Detection(s) not saved: {str(e)}')


def get_max_obj_ids(now, db_conn) -> dict:
    """Get a dictionary of labels and max object IDs for current date"""

    # calculate start of current hour
    curr_dt_start = f'{str(now.date())} 00:00:00'

    # fetch results from DB
    df = pd.read_sql(f"""
        SELECT label, COUNT (DISTINCT obj_id) as next_obj_id
        FROM object_detections
        WHERE create_ts >= :curr_dt_start
        GROUP BY 1
    """, params={'curr_dt_start': curr_dt_start}, con=db_conn)

    # convert dataframe to a {label:count} dictionary
    return {rec['label']: rec['next_obj_id'] for rec in df.to_dict(orient='records')}


def get_motion_df(db_conn) -> pd.DataFrame:
    """Get means of motion detections by hour for last N-days and today"""

    # fetch results from DB
    df = pd.read_sql(f"""
        SELECT id, create_ts, '1' as motion_count
        FROM motion_detections
        WHERE create_ts BETWEEN datetime('now', '-{config.USE_HISTORICAL_DAYS} days') AND datetime('now', 'localtime')
        GROUP BY 1,2,3
    """, con=db_conn)
    # update data types
    df.create_ts = pd.to_datetime(df.create_ts)
    df.motion_count = df.motion_count.astype(int)
    # resample data by hour
    motion_det_df_resampled = df.set_index('create_ts').resample(
        'H').count().reset_index()[['create_ts', 'motion_count']].fillna(0)
    # split historical dates and today
    td = datetime.now().date()
    motion_det_df_resampled_hist = motion_det_df_resampled.loc[motion_det_df_resampled['create_ts'].dt.date != td]
    motion_det_df_resampled_td = motion_det_df_resampled.loc[motion_det_df_resampled['create_ts'].dt.date == td]
    # calculate avg hourly count for historical detections
    motion_det_df_resampled_avg_hist = motion_det_df_resampled_hist.groupby(
        motion_det_df_resampled_hist.create_ts.dt.hour)['motion_count'].mean()
    hist = motion_det_df_resampled_avg_hist.reset_index()
    hist.columns = ['Hour', 'Historical']
    # calculate hourly count for today's detections
    motion_det_df_resampled_avg_td = motion_det_df_resampled_td.groupby(
        motion_det_df_resampled_td.create_ts.dt.hour)['motion_count'].sum()
    today = motion_det_df_resampled_avg_td.reset_index()
    today.columns = ['Hour', 'Today']
    # return merged: historical and today's datasets
    return hist.merge(today, how='left').fillna(0).set_index('Hour')


def get_object_det_df(db_conn) -> dict:
    """Get means of object detections by hour for last N-days and today"""

    # fetch detections from db
    object_det_df = pd.read_sql(f"""
        SELECT id, label, create_ts, obj_id
        FROM object_detections
        WHERE create_ts BETWEEN datetime('now', '-{config.USE_HISTORICAL_DAYS} days') AND datetime('now', 'localtime')
        GROUP BY 1,2,3,4
    """, con=db_conn)
    # update data types
    object_det_df.create_ts = pd.to_datetime(object_det_df.create_ts)
    object_det_df.obj_id = object_det_df.obj_id.astype(int)
    # initialize final results
    results = {}
    for label in config.TRACK_OBJECTS:
        # filter records only for the label
        obj_df = object_det_df.loc[object_det_df['label'] == label]

        # resample date at hourly level
        object_det_df_resampled = obj_df.set_index('create_ts').resample(
            'H').nunique().reset_index()[['label', 'create_ts', 'obj_id']]

        # fill NaN's
        idx = object_det_df_resampled['label'].isnull()
        object_det_df_resampled.loc[idx, 'label'] = label
        object_det_df_resampled.loc[idx, 'obj_id'] = 0

        # split historical dates and today
        td = datetime.now().date()
        object_det_df_resampled_hist = object_det_df_resampled.loc[object_det_df_resampled['create_ts'].dt.date != td]
        object_det_df_resampled_td = object_det_df_resampled.loc[object_det_df_resampled['create_ts'].dt.date == td]

        # calculate avg hourly count for historical detections
        object_det_df_resampled_avg_hist = object_det_df_resampled_hist.groupby(
            object_det_df_resampled_hist.create_ts.dt.hour)['obj_id'].mean()
        hist = object_det_df_resampled_avg_hist.reset_index()
        hist.columns = ['Hour', 'Historical']

        # calculate avg hourly count for today's detections
        object_det_df_resampled_avg_td = object_det_df_resampled_td.groupby(
            object_det_df_resampled_td.create_ts.dt.hour)['obj_id'].mean()
        today = object_det_df_resampled_avg_td.reset_index()
        today.columns = ['Hour', 'Today']
        # add to results
        results[label] = hist.merge(today, how='left').fillna(0).set_index('Hour')
    return results

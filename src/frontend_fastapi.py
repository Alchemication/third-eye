import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import pandas as pd
from datetime import datetime
import os
import config
from socket import gethostname
import random
from database import engine
from detections import get_motion_analysis, get_objects_analysis
from command_centre import get_open_stream_url
from heart_beat import fetch_last_heart_beat, is_healthy

# set up logger
logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt=config.LOGGING_DATE_FORMAT)
logger = logging.getLogger()

# start FastAPI app
logging.info('Starting FastAPI app...')
app = FastAPI()

# mount static folders
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory=config.IMG_FOLDER), name="images")

# point Jinja2 to templates directory
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render main HTML template and pass required view variables"""
    # create a random number (handy to prevent browser caching issues)
    cache_id = random.random()
    # find out the stream URL (use public URL if a stream is currently open,
    # otherwise use the config value)
    open_stream_url = get_open_stream_url()
    stream_url = f'{open_stream_url or config.VIDEO_STREAM_BASE_URL}/{config.VIDEO_STREAM_PATH}'
    return templates.TemplateResponse("index.html", {
        "request": request,
        "msg": "Hello, World",
        "video_feed_url": stream_url,
        "cache_id": cache_id,
        "hostname": gethostname(),
        "config": {
            "file_identifiers": [config.INTRUDER_FILES_IDENTIFIER, config.HEART_BEAT_FILES_IDENTIFIER],
            "use_historical_days": config.USE_HISTORICAL_DAYS
        }
    })


@app.get('/analysis')
async def fetch_detections_analysis(at: str):
    """
    Return summary of today's detections vs last 6 days avg
    :param at: analysis_type: motion or objects - will determine which type of results to return
    """
    try:
        # check analysis-type (at) in query string and fetch appropriate DB call
        results = get_motion_analysis(engine) if at == 'motion' else get_objects_analysis(engine)
    except Exception as e:
        return {"**ERROR**": str(e)}, 500
    return results


@app.get('/heart-beat')
async def heart_beat():
    """Return last heart beat recorded in the DB"""
    try:
        # grab last heart beat from the DB
        last_heart_beat = fetch_last_heart_beat()
        # determine if last heart beat occurred within specified time
        heart_beat_status = is_healthy(last_heart_beat)
    except Exception as e:
        return {"**ERROR**": str(e)}, 500
    return {"hb": last_heart_beat, "is_ok": heart_beat_status}


@app.get('/get-images')
async def get_images(inc_im_types: str, from_date: str, to_date: str, from_time: str, to_time: str):
    # image types will be easier to compare if they are a list
    inc_im_types = inc_im_types.split(',')
    filtered_files, filtered_timestamps = [], []
    for dt in pd.date_range(from_date, to_date, freq='D'):
        dt_dir = str(dt.date())
        dt_full_path = f'{config.IMG_FOLDER}/{dt_dir}'
        if not os.path.exists(dt_full_path):
            continue
        # define from timestamp and to timestamp
        min_ts = datetime.strptime(f'{dt_dir} {from_time}', '%Y-%m-%d %H:%M')
        max_ts = datetime.strptime(f'{dt_dir} {to_time}:59.999999', '%Y-%m-%d %H:%M:%S.%f')
        all_images_in_path = [f for f in os.listdir(dt_full_path)]
        all_images_in_path.sort()
        for f in all_images_in_path:
            img_ts = datetime.strptime(f'{dt_dir} {f[:13]}', '%Y-%m-%d %H%M%S.%f')
            for im_type in inc_im_types:
                if im_type in f and min_ts <= img_ts <= max_ts:
                    filtered_files.append(f'{dt_dir}/{f}')
                    filtered_timestamps.append(img_ts)
    return {'files': filtered_files, 'timestamps': filtered_timestamps}

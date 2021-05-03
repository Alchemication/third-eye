import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import config
from socket import gethostname
import random
from database import engine
from detections import get_motion_analysis, get_objects_analysis
from command_centre import get_open_stream_url

# set up logger
logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt="%H:%M:%S")
logger = logging.getLogger()

# start FastAPI app
logging.info('Starting FastAPI app...')
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
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
        "hostname": gethostname()
    })


@app.get('/analysis')
async def fetch_detections_analysis(at: str):
    try:
        # check analysis-type (at) in query string and fetch appropriate DB call
        results = get_motion_analysis(engine) if at == 'motion' else get_objects_analysis(engine)
    except Exception as e:
        return {"**ERROR**": str(e)}, 500
    return results

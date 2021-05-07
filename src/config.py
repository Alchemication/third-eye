import logging
import os


# app title
APP_NAME = 'Third Eye'

# video/image resolution
STREAM_RES = (1280, 720)  # 720p <- faster ~20 FPS on RPi4
# STREAM_RES = (1920, 1080)  # 1080p <- more choppy ~12 FPS on RPi4

# enabling debug mode will show video in reduced resolution
# with bounding boxes around detected objects
APP_DEBUG_MODE = False

# paths
BASE_DIR = '/home/pi/Laboratory/third-eye'
DB_FILE_PATH = f'{BASE_DIR}-db/app.db'
IMG_FOLDER = f'{BASE_DIR}-images'

# define how console logs will be displayed (default INFO,
# set to DEBUG for troubleshooting and dev, and ERROR for
# low-noise mode)
LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = "%(asctime)s.%(msecs)03f - %(name)s - %(levelname)s - %(message)s"
LOGGING_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# do SQL queries need to be displayed (sql-alchemy parameter)?
LOG_DB_EVENTS = False

# URL for the stream (will be used if there are no public streams open)
VIDEO_STREAM_BASE_URL = 'http://192.168.1.187:8000'
VIDEO_STREAM_PATH = 'video-feed'

# Heart beat configuration, when enabled - backend
# will be sending heart beat images every N-seconds to
# the message queue listening for heart beats
HEART_BEAT_ENABLED = True
HEART_BEAT_PUB_URL = 'tcp://*:5555'
HEART_BEAT_SUB_URL = 'tcp://127.0.0.1:5555'
HEART_BEAT_INTERVAL_N_FRAMES = 200
HEART_BEAT_INTERVAL_MAX_IDLE_N_SEC = 60
HEART_BEAT_IMAGES_KEEP_N_DAYS = 14
HEART_BEAT_FILES_IDENTIFIER = 'HEART-BEAT'

# Set up stream properties, set these if the camera used requires some adjustments
STREAM_PROPS = (
    # (cv2.CAP_PROP_BRIGHTNESS, 50),
    # (cv2.CAP_PROP_SATURATION, 60),
    # (cv2.CAP_PROP_CONTRAST, 100)
)

# Toggle displaying in the UI if home owners are at home
SHOW_HOME_OCCUPANCY_STATUS = False

# Define secure zone (which will be used to detect potential intruders),
# this needs to be defined for every camera location individually,
# the assumption is that the resized frame is 400 in width, and 225 in height,
# and below is a list of points, which will be connected to create a poly shape
SECURE_ZONE_POLY = [[1, 8], [100, 6], [200, 12], [300, 30], [398, 50], [398, 223], [1, 223]]

# Flip image vertically (if camera is mounted upside down)
FLIP_IMAGE = True

# Cache DB calls
DETECTIONS_DATA_CACHE_TTL = 10
OCCUPANCY_DATA_CACHE_TTL = 2

# How many days use for historical data vs today charts
USE_HISTORICAL_DAYS = 7

# motion detection parameters
BG_SUB_HISTORY = 100
BG_SUB_THRESH = 40
BG_SUB_SHADOWS = False
MIN_OBJ_AREA = 80
MIN_MOTION_FRAMES = 6

# object detection model and labels location
MODEL_FILE = f'{BASE_DIR}/src/models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'
LABELS_FILE = f'{BASE_DIR}/src/models/coco_labels.txt'

# minimum probability to filter weak detections (and prevent false positives)
PRED_CONFIDENCE = 0.5

# max distance to link objects as same in object tracking
MAX_SAME_OBJ_DIST = 30

# detect only these objects
TRACK_OBJECTS = ('person', 'car', 'truck', 'bird', 'cat', 'dog')

# probabilities for each object type when generating synthetic data (for dev/testing)
OBJ_PROBA = (0.3, 0.3, 0.1, 0.1, 0.1, 0.1)

# define MAC addresses to detect home owners (need to be on Wi-Fi),
# it's a good idea to disable Private IP Address for home Wi-Fi's,
# otherwise single device will have a few dynamic Mac addresses for
# each network (if one has a few in a single house)
SUBNET_MASK = '192.168.1.0/24'
HOME_OWNERS_MAC_ADDR = [{'mac_addr': '20:E8:74:00:B8:15', 'owner': 'Edo', 'device': 'phone'},
                        {'mac_addr': '44:F2:1B:29:C3:ED', 'owner': 'Enio', 'device': 'phone'}]

# if home owner devices have not been detected in Wi-Fi for N-minutes,
# system will qualify them as outside
OWNERS_OUTSIDE_HOME_MIN = 20

# set the hours between which will be triggered even when house is occupied by owners
# - to disable: set to None to disable this feature,
# - to enable: set to list of tuples, example from 24:00:00 to 04:59:59AM: [(24, 4)]
SECURITY_ON_OVERRIDE_HOURS = [(24, 4)]

# define objects, which can trigger security alerts
INTRUDER_OBJECTS = ['person', 'cat', 'dog']

# if objects of interest have been detected in an image,
# wait this many seconds before checking if alert needs to be triggered
MIN_SEC_ALERT_CHECK = 3

# if an alert was already sent within this many seconds, do not send another one
MIN_SEC_BETWEEN_ALERTS = 60

# configuration for SMS notifications
# most of the items for security reasons need to be
# inserted as environmental variables
SMS_NOTIFICATIONS_ENABLED = True
TWILIO_PHONE_NUMBER = os.environ['TWILIO_PHONE_NUMBER']
TWILIO_SID = os.environ['TWILIO_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']

# these numbers will receive SMS notifications,
# example format: +353861234,+353871234
NOTIFY_PHONE_NUMBERS = os.environ['NOTIFY_PHONE_NUMBERS'].split(',')

# configuration for Email notifications
EMAIL_NOTIFICATIONS_ENABLED = True
SMTP_SERVER_HOST = os.environ['SMTP_SERVER_HOST']  # example: smtp.gmail.com
SMTP_SERVER_PORT = int(os.environ['SMTP_SERVER_PORT'])  # example: 587 for TLS
EMAIL_SENDER_ADDRESS = os.environ['EMAIL_SENDER_ADDRESS']
EMAIL_SENDER_PASSWORD = os.environ['EMAIL_SENDER_PASSWORD']

# these emails will receive Email notifications,
# example format: adam12@gmail.com,anna81@gmail.com
RECEIVER_EMAIL_ADDRESSES = os.environ['RECEIVER_EMAIL_ADDRESSES'].split(',')  # comma separated list of addresses

# API Key to open up/access the stream to the outside world
STREAM_API_KEY = os.environ['STREAM_API_KEY']

# how many minutes to open up the stream access for
STREAM_EXPIRY_SEC = 180

from fastapi import FastAPI
import numpy as np
from starlette.responses import StreamingResponse
import cv2
from imutils.video import VideoStream
import threading
import imutils
import config
from detections import get_max_obj_ids, save_detections, get_obj_det_comps
from security import check_alerts
import logging
import time
from datetime import datetime
import simplejpeg
from PIL import Image
from object_tracker import EuclideanDistTracker
import importlib
from database import engine
from models import MotionDetection, ObjectDetection


# set up logger
logging.basicConfig(format="%(asctime)s.%(msecs)03f %(levelname)s %(message)s",
                    level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()
logger.setLevel(config.LOGGING_LEVEL)


# check if running in debug mode
if config.APP_DEBUG_MODE:
    logging.info('===== Running in debug mode =====')

# start FastAPI app
logging.info('Starting FastAPI app...')
app = FastAPI()

# initialize global app vars
output_frame = None
lock = threading.Lock()


def get_obj_trackers(max_dist, track_objects, now) -> dict:
    """Create an instance of Object Tracker for each label"""
    logging.info("Creating object trackers")
    try:
        max_obj_ids = get_max_obj_ids(now, engine)
    except Exception as e:
        logger.error('Could not retrieve max object IDs for today')
        raise e
    # each tracker will be initialized with the last ID registered in the DB in last hour
    object_trackers = {label: EuclideanDistTracker(id_start=max_obj_ids[label] if label in max_obj_ids else 0,
                                                   max_distance=max_dist) for label in track_objects}
    return object_trackers


def get_video_stream(cam_src: int = 0) -> VideoStream:
    """Initialize stream from the camera, source=0 -> WebCam, source=1 -> PyCam"""
    logging.info('Starting video stream...')
    vs = VideoStream(src=cam_src, resolution=config.STREAM_RES).start()
    # update stream properties, like brightness, contrast, etc. (if it's defined in the config)
    for props in config.STREAM_PROPS:
        vs.stream.set(props[0], props[1])
    return vs


def process_frames(object_trackers, model, labels):
    """
    Execute processing pipeline to the frames from the camera:
    - motion detection
    - object detection
    :return: None
    """
    logging.info('Processing frames...')

    # grab necessary global references
    global output_frame, lock, video_stream

    # initialize background subtractor for motion detection
    bg_subtr = cv2.createBackgroundSubtractorMOG2(history=config.BG_SUB_HISTORY,
                                                  varThreshold=config.BG_SUB_THRESH,
                                                  detectShadows=config.BG_SUB_SHADOWS)

    # initialize variable to keep track of consecutive motion frames
    motion_frames = 0

    # initialize params used to measure single frame processing time
    counter = 0
    proc_times = []

    # set motion detector to not-ready initially (it needs to have
    # a few frames to learn the background)
    motion_detector_ready = False

    # is checking for alerts needed, initialize by True,
    # and then after each alert check set to False for N-seconds,
    # so we are not constantly firing DB queries and saving images,
    # (alert check will run in a separate thread)
    is_check_alert = True
    last_alert_check_ts = None

    # initialize current day, as we need to reset object trackers on a new day
    curr_day = datetime.now().day

    # loop over frames from the video stream
    while True:

        # if in debug mode, reimport the config on the fly (so we can
        # tweak config values and see results immediately in the stream)
        if config.APP_DEBUG_MODE:
            importlib.reload(config)

        # initialize start time to calculate time to process 1 frame
        curr_frame_ts = datetime.now()

        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = video_stream.read()

        # update stream properties in debug mode
        if config.APP_DEBUG_MODE:
            for props in config.STREAM_PROPS:
                video_stream.stream.set(props[0], props[1])

        # mirror image horizontally to show the real "you"
        frame = cv2.flip(frame, 1)

        # check if camera hands upside down and vertical rotation is required
        if config.FLIP_IMAGE:
            frame = cv2.flip(frame, 0)

        # create a numpy array from secure area points, as this will
        # be needed a few times below
        secure_area_pts = np.array(config.SECURE_ZONE_POLY, np.int32).reshape((-1, 1, 2))

        # resize image to boost the performance of detectors
        frame_sm = imutils.resize(frame, width=400)

        # remove "public" area considered as not-secure (outside of secure area mask),
        # this is done to adhere to government regulations about the on-premise CCTV
        # https://www.dataprotection.ie/en/dpc-guidance/blogs/cctv-home
        # TODO: apply this method to original image as well (pixelate area outside of secure zone)
        mask = np.zeros(frame_sm.shape).astype(frame_sm.dtype)
        cv2.fillConvexPoly(mask, secure_area_pts, (255, 255, 255), lineType=cv2.LINE_AA)
        frame_sm = cv2.bitwise_and(frame_sm, mask)

        # convert to grayscale
        frame_gray = cv2.cvtColor(frame_sm, cv2.COLOR_BGR2GRAY)

        # show secure area in debug mode
        if config.APP_DEBUG_MODE:
            cv2.polylines(frame_sm, [secure_area_pts], True, (0, 0, 255))
            cv2.putText(frame_sm, 'Secure zone', (5, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

        # ===== Motion Detection ======
        # perform motion detection
        mask = bg_subtr.apply(frame_gray)

        # find contours from motion detection algorithm
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # initialize list, which will contain motion or object detections,
        # if any are detected inside the current frame
        detections = []

        # assume no motion by default for each frame
        motion_candidate = False

        # iterate through contours detected by background subtractor
        for cnt in contours:
            # check if we have enough images to detect motion
            if not motion_detector_ready:
                break

            # calculate area of detected contour
            cnt_area = cv2.contourArea(cnt)

            # if area of a contour is less than a threshold, we don't have a motion,
            # so move on to the next contour
            if cnt_area < config.MIN_OBJ_AREA:
                continue

            # indicate potential motion candidate
            motion_candidate = True

            # increment consecutive frames motion counter
            motion_frames += 1

            # break from the loop early if we don't have enough consecutive frames with motion yet
            if motion_frames < config.MIN_MOTION_FRAMES:
                break

            # at this stage we do have enough consecutive frames with motion
            # reset consecutive frames motion counter
            motion_frames = 0

            # add motion to detections, which will be bulk-saved in the DB later
            (x, y, w, h) = cv2.boundingRect(cnt)
            detections.append(MotionDetection(create_ts=curr_frame_ts, x=x, y=y, w=w, h=h,
                                              area=cnt_area))

            # ===== Object Detection ======
            # now that we know we do have the motion, we can run object detection
            # and see if we have any tracked objects in the frame

            # first, frame needs to be converted to Pillow format (this step
            # will be unnecessary when we switch to newer version of Coral lib)
            frame_pil = Image.fromarray(frame_sm)
            # now we can detect objects in the frame
            obj_det_results = model.detect_with_image(frame_pil, threshold=config.PRED_CONFIDENCE,
                                                      keep_aspect_ratio=True, relative_coord=False)
            # filter out unwanted objects
            obj_det_results = [r for r in obj_det_results if labels[r.label_id] in config.TRACK_OBJECTS]
            logging.debug(f'{len(obj_det_results)} object(s) detected')
            # loop over the results
            objects_detected = []
            object_coordinates = {}
            for r in obj_det_results:
                # extract the bounding box and box and predicted class label
                box = r.bounding_box.flatten().astype("int")
                (start_x, start_y, end_x, end_y) = box
                label = labels[r.label_id]
                # update variables used by the objects tracker
                if r.label_id not in objects_detected:
                    objects_detected.append((label, r.score))
                    object_coordinates[label] = []
                object_coordinates[label].append((start_x, start_y, end_x - start_x, end_y - start_y))
            # now update all object trackers (for each of the labels in the frame)
            for (label, score) in objects_detected:
                label_ids = object_trackers[label].update(object_coordinates[label])
                for label_id in label_ids:
                    x, y, w, h, obj_id = label_id
                    logging.debug(f'Object: {label}; x={x}, y={y}, w={w}, h={h};'
                                  f' id={obj_id}; score={score:.2f}')
                    # add to detections, which will be bulk-saved in the DB later
                    obj_detection = ObjectDetection(create_ts=curr_frame_ts, x=int(x), y=int(y),
                                                    w=int(w), h=int(h), area=int(w * h), label=label,
                                                    obj_id=obj_id, score=score)
                    detections.append(obj_detection)
                    # draw the bounding box and label+id on the image (in debug mode)
                    if config.APP_DEBUG_MODE:
                        # draw bounding box
                        cv2.rectangle(frame_sm, (x, y), (x + w, y + h),
                                      (0, 255, 0), 1)
                        # label/score/tracking ID
                        cv2.putText(frame_sm, f'{label}:{score:.2f}:ID#{obj_id}', (x, y - 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                        # draw a dot for bounding box centroid
                        cv2.circle(frame_sm, (obj_detection.cx, obj_detection.cy), 0, (0, 255, 0), -1)
            # keep only valid object detections from detections list
            valid_obj_detections = [d for d in detections if isinstance(d, ObjectDetection)
                                    and d.label in config.INTRUDER_OBJECTS]
            # calculate number of seconds since last alert check
            if len(valid_obj_detections) > 0 and last_alert_check_ts is not None and \
                    (curr_frame_ts - last_alert_check_ts).total_seconds() > config.MIN_SEC_ALERT_CHECK:
                logging.info(f'Set is_check_alert to True, curr_frame_ts is {str(curr_frame_ts)} and'
                             f' last_alert_check_ts is {str(last_alert_check_ts)}')
                is_check_alert = True
            # check for alerts if we have valid objects detected,
            # and N-seconds elapsed from previous check
            if len(valid_obj_detections) > 0 and is_check_alert is True:
                # check which frame to pass to security module (based on the debug switch)
                curr_frame = frame_sm if config.APP_DEBUG_MODE else frame
                # check alerts in a separate thread
                alerts_t = threading.Thread(target=check_alerts, args=(valid_obj_detections, curr_frame,))
                alerts_t.daemon = True
                alerts_t.start()
                # disable alert checks for N-seconds
                is_check_alert = False
                last_alert_check_ts = curr_frame_ts
                logging.info(f'Set is_check_alert to False and last_alert_check_ts to {str(curr_frame_ts)}')
            # save detections in the DB if motion has been captured in N-consecutive frames
            # TODO: check this !!
            if len(detections) > 0:
                # save detections in a separate thread
                det_t = threading.Thread(target=save_detections, args=(detections,))
                det_t.daemon = True
                det_t.start()
            break

        # reset consecutive frames motion counter if no motion was detected in the frame
        if motion_candidate is False:
            motion_frames = 0

        # calculate processing time
        time_diff = (datetime.now() - curr_frame_ts).total_seconds()

        # check if we can start the motion detection
        if not motion_detector_ready and counter != 0 and counter % config.BG_SUB_HISTORY == 0:
            logging.info(f'Motion detector ready (counter is {counter})')
            motion_detector_ready = True

        # display average processing time for each frame
        # and check if the hour has changed (if yes - reset object ID counters)
        if counter != 0 and counter % config.AVG_PROC_TIME_N_FRAMES == 0:
            logging.info(f'Avg processing time per frame:'
                         f' {sum(proc_times) / config.AVG_PROC_TIME_N_FRAMES:.2f} sec.')
            counter = 0
            proc_times = []
            # check day, and if it's changed - reset object trackers
            new_day = curr_frame_ts.day
            if new_day != curr_day:
                curr_day = new_day
                object_trackers = {label: EuclideanDistTracker(config.MAX_SAME_OBJ_DIST) for
                                   label in config.TRACK_OBJECTS}
                logging.info(f'New day of the month arrived: {curr_day}. Object trackers have been reset.')
        else:
            proc_times.append(time_diff)
            counter += 1

        # acquire the lock, set the output frame, and release the lock
        with lock:
            if config.APP_DEBUG_MODE:
                output_frame = frame_sm.copy()
            else:
                output_frame = frame.copy()


def generate():
    """
    Return continuous stream of images
    :return: binary response
    """

    # grab global references to the output frame and lock variables
    global output_frame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if output_frame is None:
                continue
            # encode the frame in JPEG format
            # simplejpeg is faster than cv2.imencode, which is actually a bottleneck in RPi
            encoded_image = simplejpeg.encode_jpeg(output_frame, quality=90, colorspace='BGR')

        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encoded_image) + b'\r\n')


@app.get("/video-feed")
def video_feed():
    # Read frames from the camera, process and return continuous stream of images
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")


# create app components
det_model, det_labels = get_obj_det_comps(config.MODEL_FILE, config.LABELS_FILE)
det_object_trackers = get_obj_trackers(config.MAX_SAME_OBJ_DIST, config.TRACK_OBJECTS, datetime.now())
video_stream = get_video_stream()


# start a thread, which will perform motion and object detection
t = threading.Thread(target=process_frames, args=(det_object_trackers, det_model, det_labels,))
t.daemon = True
t.start()

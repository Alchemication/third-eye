# Example usage: python rec_video.py -f ./videos/example.avi -d 20 -c MPEG

import cv2
from imutils.video import VideoStream
import config
import logging
import time
import argparse


def main(video_filename: str, video_duration: int, video_codec: str):
    """Record an N-second video into a file using provided codec"""

    # Initialize stream from the camera, source=0 -> WebCam, source=1 -> PyCam
    logging.info('Starting video stream...')
    vs = VideoStream(src=0, resolution=config.STREAM_RES).start()
    for props in config.STREAM_PROPS:
        vs.stream.set(props[0], props[1])

    # initialize the FourCC, video writer, dimensions of the frame, and
    # zeros array
    fourcc = cv2.VideoWriter_fourcc(*video_codec)
    writer = None

    # initialize timer
    start_time = time.process_time()

    # loop over frames from the video stream
    logging.info('Collecting frames...')
    while True:
        # read the next frame from the video stream
        frame = vs.read()

        # mirror image horizontally to show the real "you"
        frame = cv2.flip(frame, 1)

        # check if camera hands upside down and vertical rotation is required
        if config.FLIP_IMAGE:
            frame = cv2.flip(frame, 0)

        # check if the writer is None
        if writer is None:
            # store the image dimensions and initialize the video writer
            (h, w) = frame.shape[:2]
            writer = cv2.VideoWriter(video_filename, fourcc, 25, (w, h), True)
            logging.info('Setting up video writer and recording...')

        # write the output frame to file
        writer.write(frame)

        # check time and exit loop if required number of seconds is passed
        curr_time = time.process_time()
        elapsed_seconds = curr_time - start_time
        if elapsed_seconds > video_duration:
            logging.info(f'Stopping frame collection, elapsed {elapsed_seconds} second(s)...')
            break

    # do a bit of cleanup
    logging.info(f"Writing to {video_filename} and cleaning up...")
    vs.stop()
    writer.release()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--filename", type=str, required=True, help='Video clip file name')
    ap.add_argument("-d", "--duration", type=int, default=10, help='Number of seconds to stop recording')
    ap.add_argument("-c", "--codec", type=str, default="MPEG", help="Codec of output video")
    args = vars(ap.parse_args())

    # set up logger
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt="%H:%M:%S")
    logger = logging.getLogger()

    main(args['filename'], args['duration'], args['codec'])

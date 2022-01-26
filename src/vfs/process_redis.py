import argparse
import cv2
import os
import redis
import traceback
from datetime import datetime
from time import sleep
from yaml import safe_dump

from vfs.common import INPUT_IMAGE_DIR, INPUT_VIDEO, INPUT_WEBCAM, INPUT_TYPES, ANALYSIS_ROISCSV, ANALYSIS_OPEXJSON, \
    ANALYSIS_TYPES, OUTPUT_JPG, OUTPUT_MJPG, OUTPUT_TYPES, list_images
from vfs.predictions import load_roiscsv_from_str, load_opexjson_from_str, crop_frame, check_predictions
from vfs.logging import log
from vfs.prune import detect_change


def load_output(analysis_str, analysis_type, metadata):
    """
    Loads the generated analysis output file and returns the predictions.

    :param analysis_str: the file to check
    :type analysis_str: str
    :param analysis_type: the type of analysis, see ANALYSIS_TYPES
    :type analysis_type: str
    :param metadata: for attaching metadata
    :type metadata: dict
    :return: list of Prediction objects
    :rtype: list
    """
    if analysis_type == ANALYSIS_ROISCSV:
        result = load_roiscsv_from_str(analysis_str)
    elif analysis_type == ANALYSIS_OPEXJSON:
        result = load_opexjson_from_str(analysis_str)
    else:
        raise Exception("Unhandled analysis type: %s" % analysis_type)

    metadata["num_predictions"] = len(result)

    return result


class RedisConnection(object):
    """
    Container class to encapsulate the redis connection.
    """

    def __init__(self):
        self.redis = None
        self.pubsub = None
        self.pubsub_thread = None
        self.channel_out = None
        self.channel_in = None
        self.timeout = None
        self.data = None


def process_image(frame, frameno, redis_conn, analysis_type,
                  min_score, required_labels, excluded_labels,
                  crop_to_content, crop_margin, crop_min_width, crop_min_height,
                  verbose):
    """
    Pushes a frame through the image analysis framework and returns whether to keep it or not.

    :param frame: the frame to check
    :type frame: ndarray
    :param frameno: the current frame no
    :type frameno: int
    :param redis_conn: the Redis connection to use
    :type redis_conn: RedisConnection
    :param analysis_type: the type of output the analysis is generated, see ANALYSIS_TYPES
    :type analysis_type: str
    :param min_score: the minimum score that the predictions have to have
    :type min_score: float
    :param required_labels: the list of labels that must have the specified min_score, ignored if None or empty
    :type required_labels: list or None
    :param excluded_labels: the list of labels that must not have the specified min_score, ignored if None or empty
    :type excluded_labels: list or None
    :param crop_to_content: whether to crop the frame to the content (eg bounding boxes)
    :type crop_to_content: bool
    :param crop_margin: the margin to use around the cropped content
    :type crop_margin: int
    :param crop_min_width: the minimum width for the cropped content
    :type crop_min_width: int
    :param crop_min_height: the minimum height for the cropped content
    :type crop_min_height: int
    :param verbose: whether to print some logging information
    :type verbose: bool
    :return: tuple (whether to keep the frame or skip it, potentially cropped frame, metadata)
    :rtype: tuple
    """
    frame_str = cv2.imencode('.jpg', frame)[1].tobytes()
    metadata = dict()

    def anon_handler(message):
        data = message['data']
        redis_conn.data = data
        redis_conn.pubsub_thread.stop()
        redis_conn.pubsub.close()
        redis_conn.pubsub = None

    redis_conn.pubsub = redis_conn.redis.pubsub()
    redis_conn.pubsub.psubscribe(**{redis_conn.channel_in: anon_handler})
    redis_conn.pubsub_thread = redis_conn.pubsub.run_in_thread(sleep_time=0.001)
    redis_conn.redis.publish(redis_conn.channel_out, frame_str)

    # wait for data to show up
    start = datetime.now()
    no_data = False
    while redis_conn.pubsub is not None:
        sleep(0.01)
        if redis_conn.timeout > 0:
            end = datetime.now()
            if (end - start).total_seconds() >= redis_conn.timeout:
                if verbose:
                    log("Timeout reached!")
                no_data = True
                break

    if no_data:
        return False, frame, metadata

    predictions = load_output(redis_conn.data, analysis_type, metadata)
    result = check_predictions(predictions, min_score, required_labels, excluded_labels, verbose)
    if verbose:
        log("Can be included: %s" % str(result))
    if result:
        if crop_to_content:
            frame = crop_frame(frame, predictions, metadata,
                               margin=crop_margin, min_width=crop_min_width, min_height=crop_min_height,
                               verbose=verbose)
    return result, frame, metadata


def process(input, input_type, nth_frame, max_frames, redis_conn,
            analysis_type, from_frame, to_frame,
            min_score, required_labels, excluded_labels,
            output, output_type, output_format, output_tmp, output_fps, output_metadata,
            crop_to_content, crop_margin, crop_min_width, crop_min_height,
            verbose, progress, keep_original, prune, bw_threshold, change_threshold):
    """
    Processes the input video or webcam feed.
    
    :param input: the input dir, video or webcam ID
    :type input: str
    :param input_type: the type of input, INPUT_TYPES
    :type input_type: str
    :param nth_frame: for frame skipping to speed up processing
    :type nth_frame: int
    :param max_frames: the maximum number of processed frames before exiting (<=0 for unlimited)
    :type max_frames: int
    :param redis_conn: the Redis connection to use
    :type redis_conn: RedisConnection
    :param analysis_type: the type of output the analysis is generated, see ANALYSIS_TYPES
    :type analysis_type: str
    :param from_frame: the starting frame (incl), ignored if <=0
    :type from_frame: int
    :param to_frame: the last frame (incl), ignored if <=0
    :type to_frame: int
    :param min_score: the minimum score that the predictions have to have
    :type min_score: float
    :param required_labels: the list of labels that must have the specified min_score, ignored if None or empty
    :type required_labels: list
    :param excluded_labels: the list of labels that must not have the specified min_score, ignored if None or empty
    :type excluded_labels: list
    :param output: the output video oor directory for output images
    :type output: str
    :param output_type: the type of output to generate, see OUTPUT_TYPES
    :type output_type: str
    :param output_format: the file name format to use for the image files
    :type output_format: str
    :param output_tmp: the tmp directory to write the output images to before moving them to the output directory
    :type output_tmp: str
    :param output_fps: the frames-per-second to use when generating an output video
    :type output_fps: int
    :param output_metadata: whether to output metadata as YAML file alongside JPG frames
    :type output_metadata: bool
    :param crop_to_content: whether to crop the frame to the content (eg bounding boxes)
    :type crop_to_content: bool
    :param crop_margin: the margin to use around the cropped content
    :type crop_margin: int
    :param crop_min_width: the minimum width for the cropped content
    :type crop_min_width: int
    :param crop_min_height: the minimum height for the cropped content
    :type crop_min_height: int
    :param verbose: whether to print some logging information
    :type verbose: bool
    :param progress: in verbose mode, outputs a progress line every x frames with how many frames have been processed
    :type progress: int
    :param keep_original: whether to keep the original filename when processing an image dir
    :type keep_original: bool
    :param prune: whether to discard images if they isn't enough change between them
    :type prune: bool
    :param bw_threshold: the threshold (0-255) for the black/white conversion (requires prune)
    :type bw_threshold: int
    :param change_threshold: the threshold (0.0-1.0) for the change detection (requires prune)
    :type change_threshold: float
    """

    # open input
    if input_type not in INPUT_TYPES:
        raise Exception("Unknown input type: %s" % input_type)
    cap = None
    files = None
    if input_type == INPUT_IMAGE_DIR:
        files = list_images(input, verbose=verbose)
    elif input_type == INPUT_VIDEO:
        if verbose:
            log("Opening input video: %s" % input)
        cap = cv2.VideoCapture(input)
    elif input_type == INPUT_WEBCAM:
        if verbose:
            log("Opening webcam: %s" % input)
        cap = cv2.VideoCapture(int(input))
    else:
        raise Exception("Unhandled input type: %s" % input_type)

    # frames
    if (from_frame > 0) and (to_frame > 0):
        if from_frame > to_frame:
            raise Exception("from_frame (%d) cannot be larger than to_frame (%d)" % (from_frame, to_frame))

    # analysis
    if analysis_type not in ANALYSIS_TYPES:
        raise Exception("Unknown analysis type: %s" % analysis_type)

    # open output
    out = None
    if output_type not in OUTPUT_TYPES:
        raise Exception("Unknown output type: %s" % output_type)
    if output_type == OUTPUT_MJPG:
        if verbose:
            log("Opening output video: %s" % output)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(output, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), output_fps, (frame_width, frame_height))
        crop_to_content = False
    elif output_type == OUTPUT_JPG:
        if (output_format % 1) == output_format:
            raise Exception("Output format does not expand integers: %s" % output_format)
    else:
        raise Exception("Unhandled output type: %s" % output_type)

    # iterate frames
    count = 0
    frames_count = 0
    frames_processed = 0
    frame_curr = None
    frame_prev = None
    while ((cap is not None) and cap.isOpened()) or (files is not None):
        # next frame
        if cap is not None:
            retval, frame_curr = cap.read()
        else:
            retval = frames_count < len(files)
            if retval:
                frame_curr = cv2.imread(files[frames_count])
        count += 1
        frames_count += 1

        if frames_count % progress == 0:
            log("Frames processed: %d" % frames_count)

        # check frame window
        if (from_frame > 0) and (frames_count < from_frame):
            continue
        if (to_frame > 0) and (frames_count > to_frame):
            log("Reached to_frame (%d)" % to_frame)
            break

        if (max_frames > 0) and (frames_processed >= max_frames):
            if verbose:
                log("Maximum number of processed frames reached: %d" % frames_processed)
            break

        # process frame
        if retval:
            if count >= nth_frame:
                count = 0

                # prune?
                if prune:
                    # nothing to compare?
                    if frame_prev is None:
                        frame_prev = frame_curr
                        frame_curr = None
                        continue
                    try:
                        change, above = detect_change(frame_prev, frame_curr, bw_threshold=bw_threshold,
                                                      change_threshold=change_threshold)
                    except Exception:
                        frame_prev = None
                        frame_curr = None
                        log("Failed to compare frames (current frame: %d), skipping!" % frames_count)
                        traceback.print_exc()
                        continue
                    if not above:
                        if verbose:
                            log("Frame #%d not above threshold, skipping: %f < %f" % (frames_count, change, change_threshold))
                        continue

                # do we want to keep frame?
                keep, frame, metadata = process_image(frame, frames_count, redis_conn, analysis_type, min_score,
                                                      required_labels, excluded_labels, crop_to_content,
                                                      crop_margin, crop_min_width, crop_min_height, verbose)
                if not keep:
                    continue

                frames_processed += 1

                if out is not None:
                    out.write(frame_curr)
                else:
                    # keep original filename when using image_dir
                    tmp_file = None
                    if (files is not None) and keep_original:
                        if output_tmp is not None:
                            tmp_file = os.path.join(output_tmp, os.path.basename(files[frames_count - 1]))
                        out_file = os.path.join(output, os.path.basename(files[frames_count - 1]))
                    else:
                        if output_tmp is not None:
                            tmp_file = os.path.join(output_tmp, output_format % frames_count)
                        out_file = os.path.join(output, output_format % frames_count)
                    if output_tmp is not None:
                        cv2.imwrite(tmp_file, frame_curr)
                        os.rename(tmp_file, out_file)
                        if verbose:
                            log("Frame written to: %s" % out_file)
                        if output_metadata and (metadata is not None):
                            tmp_file = os.path.splitext(tmp_file)[0] + ".yaml"
                            out_file = os.path.splitext(out_file)[0] + ".yaml"
                            with open(tmp_file, "w") as yf:
                                safe_dump(metadata, yf)
                            os.rename(tmp_file, out_file)
                            if verbose:
                                log("Meta-data written to: %s" % out_file)
                    else:
                        cv2.imwrite(out_file, frame_curr)
                        if verbose:
                            log("Frame written to: %s" % out_file)
                        if output_metadata and (metadata is not None):
                            out_file = os.path.splitext(out_file)[0] + ".yaml"
                            with open(out_file, "w") as yf:
                                safe_dump(metadata, yf)
                            if verbose:
                                log("Meta-data written to: %s" % out_file)
        else:
            break

    log("Frames processed: %d" % frames_count)

    if cap is not None:
        cap.release()
    if out is not None:
        out.release()


def main(args=None):
    """
    The main method for parsing command-line arguments and running the application.

    :param args: the commandline arguments, uses sys.argv if not supplied
    :type args: list
    """
    parser = argparse.ArgumentParser(
        prog="vfs-process-redis",
        description="Tool for replaying videos or grabbing frames from webcam, presenting it to an image analysis "
                    + "framework to determine whether to include the frame in the output. Uses Redis to exchange data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--input", metavar="DIR_OR_FILE_OR_ID", help="the dir with images, video file to read or the webcam ID", required=True)
    parser.add_argument("--input_type", help="the input type", choices=INPUT_TYPES, required=True)
    parser.add_argument("--nth_frame", metavar="INT", help="every nth frame gets presented to the analysis process", required=False, type=int, default=10)
    parser.add_argument("--max_frames", metavar="INT", help="the maximum number of processed frames before exiting (<=0 for unlimited)", required=False, type=int, default=0)
    parser.add_argument("--from_frame", metavar="INT", help="the starting frame (incl.); ignored if <= 0", required=False, type=int, default=-1)
    parser.add_argument("--to_frame", metavar="INT", help="the last frame to process (incl.); ignored if <= 0", required=False, type=int, default=-1)
    parser.add_argument("--prune", help="whether to prune the images if not enough change", action="store_true", required=False)
    parser.add_argument("--bw_threshold", metavar="INT", default=128, type=int, help="The threshold (0-255) for the black/white conversion (requires --prune)")
    parser.add_argument("--change_threshold", metavar="FLOAT", default=0.0, type=float, help="The threshold (0.0-1.0) for the change detection (requires --prune)")
    parser.add_argument('--redis_host', metavar='HOST', required=False, default="localhost", help='The redis server to connect to')
    parser.add_argument('--redis_port', metavar='PORT', required=False, default=6379, type=int, help='The port the redis server is listening on')
    parser.add_argument('--redis_db', metavar='DB', required=False, default=0, type=int, help='The redis database to use')
    parser.add_argument('--redis_out', metavar='CHANNEL', required=True, type=str, help='The redis channel to send the frames to')
    parser.add_argument('--redis_in', metavar='CHANNEL', required=True, type=str, help='The redis channel to receive the predictions on')
    parser.add_argument("--redis_timeout", metavar="SECONDS", help="the maximum number of seconds to wait for the image analysis to finish processing", required=False, type=float, default=10)
    parser.add_argument("--analysis_type", help="the type of output the analysis process generates", choices=ANALYSIS_TYPES, required=False, default=ANALYSIS_TYPES[0])
    parser.add_argument("--min_score", metavar="FLOAT", help="the minimum score that a prediction must have", required=False, type=float, default=0.0)
    parser.add_argument("--required_labels", metavar="LIST", help="the comma-separated list of labels that the analysis output must contain (with high enough scores)", required=False)
    parser.add_argument("--excluded_labels", metavar="LIST", help="the comma-separated list of labels that the analysis output must not contain (with high enough scores)", required=False)
    parser.add_argument("--output", metavar="DIR_OR_FILE", help="the output directory or file for storing the selected frames (use .avi or .mkv for videos)", required=True)
    parser.add_argument("--output_type", help="the type of output to generate", choices=OUTPUT_TYPES, required=True)
    parser.add_argument("--output_format", metavar="FORMAT", help="the format string for the images, see https://docs.python.org/3/library/stdtypes.html#old-string-formatting", required=False, default="%06d.jpg")
    parser.add_argument("--output_tmp", metavar="DIR", help="the temporary directory to write the output images to before moving them to the output directory (to avoid race conditions with processes that pick up the images)", required=False)
    parser.add_argument("--output_fps", metavar="FORMAT", help="the frames per second to use when generating a video", required=False, type=int, default=25)
    parser.add_argument("--crop_to_content", help="whether to crop the frame to the detected content", action="store_true", required=False)
    parser.add_argument("--crop_margin", metavar="INT", help="the margin in pixels to use around the determined crop region", required=False, type=int, default=0)
    parser.add_argument("--crop_min_width", metavar="INT", help="the minimum width for the cropped content", required=False, type=int, default=2)
    parser.add_argument("--crop_min_height", metavar="INT", help="the minimum height for the cropped content", required=False, type=int, default=2)
    parser.add_argument("--output_metadata", help="whether to output a YAML file alongside the image with some metadata when outputting frame images", required=False, action="store_true")
    parser.add_argument("--progress", metavar="INT", help="every nth frame a progress message is output on stdout", required=False, type=int, default=100)
    parser.add_argument("--keep_original", help="keeps the original file name when processing an image dir", action="store_true", required=False)
    parser.add_argument("--verbose", help="for more verbose output", action="store_true", required=False)
    parsed = parser.parse_args(args=args)

    # parse labels
    required_labels = None
    if parsed.required_labels is not None:
        required_labels = parsed.required_labels.split(",")
    excluded_labels = None
    if parsed.excluded_labels is not None:
        excluded_labels = parsed.excluded_labels.split(",")

    # setup redis connection
    redis_conn = RedisConnection()
    redis_conn.redis = redis.Redis(host=parsed.redis_host, port=parsed.redis_port, db=parsed.redis_db)
    redis_conn.channel_in = parsed.redis_in
    redis_conn.channel_out = parsed.redis_out
    redis_conn.timeout = parsed.redis_timeout

    process(input=parsed.input, input_type=parsed.input_type, nth_frame=parsed.nth_frame, max_frames=parsed.max_frames,
            redis_conn=redis_conn, analysis_type=parsed.analysis_type,
            from_frame=parsed.from_frame, to_frame=parsed.to_frame,
            min_score=parsed.min_score, required_labels=required_labels, excluded_labels=excluded_labels,
            output=parsed.output, output_type=parsed.output_type, output_format=parsed.output_format,
            output_tmp=parsed.output_tmp, output_fps=parsed.output_fps, output_metadata=parsed.output_metadata,
            crop_to_content=parsed.crop_to_content, crop_margin=parsed.crop_margin,
            crop_min_width=parsed.crop_min_width, crop_min_height=parsed.crop_min_height,
            verbose=parsed.verbose, progress=parsed.progress, keep_original=parsed.keep_original,
            prune=parsed.prune, bw_threshold=parsed.bw_threshold, change_threshold=parsed.change_threshold)


def sys_main():
    """
    Runs the main function using the system cli arguments, and
    returns a system error code.
    :return: 0 for success, 1 for failure.
    :rtype: int
    """
    try:
        main()
        return 0
    except Exception:
        print(traceback.format_exc())
        return 1


if __name__ == '__main__':
    main()

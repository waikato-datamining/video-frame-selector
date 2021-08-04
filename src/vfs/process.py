import argparse
import cv2
import os
import traceback
from datetime import datetime
from time import sleep
from yaml import safe_dump
from vfs.predictions import load_roiscsv, crop_frame
from vfs.logging import log


INPUT_VIDEO = "video"
INPUT_WEBCAM = "webcam"
INPUT_TYPES = [INPUT_VIDEO, INPUT_WEBCAM]
""" The available input types. """

ANALYSIS_ROISCSV = "rois_csv"
ANALYSIS_TYPES = [ANALYSIS_ROISCSV]
""" The available analysis file types. """

OUTPUT_JPG = "jpg"
OUTPUT_MJPG = "mjpg"
OUTPUT_TYPES = [OUTPUT_JPG, OUTPUT_MJPG]
""" The available output types. """

ANALYSIS_FORMAT = "%06d.EXT"
""" The file name format to use for the image analysis framework. """


def load_output(analysis_file, analysis_type, metadata):
    """
    Loads the generated analysis output file and returns the predictions.

    :param analysis_file: the file to check
    :type analysis_file: str
    :param analysis_type: the type of analysis, see ANALYSIS_TYPES
    :type analysis_type: str
    :param metadata: for attaching metadata
    :type metadata: dict
    :return: list of Prediction objects
    :rtype: list
    """
    if analysis_type == ANALYSIS_ROISCSV:
        result = load_roiscsv(analysis_file)
    else:
        raise Exception("Unhandled analysis type: %s" % analysis_type)

    metadata["num_predictions"] = len(result)

    return result


def check_predictions(predictions, min_score, required_labels, excluded_labels, verbose):
    """
    Checks whether the frame processed by the image analysis process can be included in the output.

    :param predictions: the list of Prediction objects to check
    :type predictions: list
    :param min_score: the minimum score the predictions must have to be considered
    :type min_score: float
    :param required_labels: the list of labels that must have the specified min_score, ignored if None
    :type required_labels: list or None
    :param excluded_labels: the list of labels that must not have the specified min_score, ignored if None
    :type excluded_labels: list or None
    :param verbose: whether to print some logging information
    :type verbose: bool
    :return: whether to include the frame or not
    :rtype: bool
    """

    if (required_labels is None) and (excluded_labels is None):
        return True

    # check predictions
    result = None
    for p in predictions:
        if (required_labels is not None) and (len(required_labels) > 0):
            if (p.label in required_labels) and (p.score >= min_score):
                if verbose:
                    log("Required label '%s' has score of %f (>= min score: %f)" % (p.label, p.score, min_score))
                result = True

        if (excluded_labels is not None) and (len(excluded_labels) > 0):
            if (p.label in excluded_labels) and (p.score >= min_score):
                if verbose:
                    log("Excluded label '%s' has score of %f (>= min score: %f)" % (p.label, p.score, min_score))
                result = False
    if result is None:
        result = False

    return result


def process_image(frame, frameno, analysis_input, analysis_output, analysis_tmp,
                  analysis_timeout, analysis_type, analysis_keep_files,
                  min_score, required_labels, excluded_labels, poll_interval,
                  crop_to_content, crop_margin, crop_min_width, crop_min_height,
                  verbose):
    """
    Pushes a frame through the image analysis framework and returns whether to keep it or not.

    :param frame: the frame to check
    :type frame: ndarray
    :param frameno: the current frame no
    :type frameno: int
    :param analysis_input: the input directory of the image analysis process
    :type analysis_input: str
    :param analysis_output: the output directory of the image analysis process
    :type analysis_output: str
    :param analysis_tmp: the tmp directory to write the image to before moving it into the image analysis input dir
    :type analysis_tmp: str or None
    :param analysis_timeout: the number of seconds to wait for analysis to finish before skipping frame
    :type analysis_timeout: float
    :param analysis_type: the type of output the analysis is generated, see ANALYSIS_TYPES
    :type analysis_type: str
    :param analysis_keep_files: whether to keep the analysis files rather than deleting them
    :type analysis_keep_files: bool
    :param min_score: the minimum score that the predictions have to have
    :type min_score: float
    :param required_labels: the list of labels that must have the specified min_score, ignored if None or empty
    :type required_labels: list or None
    :param excluded_labels: the list of labels that must not have the specified min_score, ignored if None or empty
    :type excluded_labels: list or None
    :param poll_interval: the interval in seconds for the file polling
    :type poll_interval: float
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
    :return: tuple (whether to keep the frame or skip it, potentially cropped frame)
    :rtype: tuple
    """
    if analysis_tmp is not None:
        img_tmp_file = os.path.join(analysis_tmp, (ANALYSIS_FORMAT % frameno).replace(".EXT", ".jpg"))
        img_in_file = os.path.join(analysis_input, (ANALYSIS_FORMAT % frameno).replace(".EXT", ".jpg"))
        if verbose:
            log("Writing image: %s" % img_tmp_file)
        cv2.imwrite(img_tmp_file, frame)
        if verbose:
            log("Renaming image to: %s" % img_in_file)
        os.rename(img_tmp_file, img_in_file)
    else:
        img_in_file = os.path.join(analysis_input, (ANALYSIS_FORMAT % frameno).replace(".EXT", ".jpg"))
        if verbose:
            log("Writing image: %s" % img_in_file)
        cv2.imwrite(img_in_file, frame)
    img_out_file = os.path.join(analysis_output, (ANALYSIS_FORMAT % frameno).replace(".EXT", ".jpg"))

    if analysis_type == ANALYSIS_ROISCSV:
        name1 = (ANALYSIS_FORMAT % frameno).replace(".EXT", "-rois.csv")
        name2 = (ANALYSIS_FORMAT % frameno).replace(".EXT", ".csv")
        out_files = [os.path.join(analysis_output, name1), os.path.join(analysis_output, name2)]
    else:
        raise Exception("Unhandled analysis type: %s" % analysis_type)

    metadata = dict()

    # pass through image analysis
    end = datetime.now().microsecond + analysis_timeout * 10e6
    while datetime.now().microsecond < end:
        for out_file in out_files:
            if os.path.exists(out_file):
                if verbose:
                    log("Checking analysis output: %s" % out_file)
                predictions = load_output(out_file, analysis_type, metadata)
                result = check_predictions(predictions, min_score, required_labels, excluded_labels, verbose)
                if not analysis_keep_files:
                    os.remove(out_file)
                if verbose:
                    log("Can be included: %s" % str(result))
                if result:
                    if crop_to_content:
                        frame = crop_frame(frame, predictions, metadata,
                                           margin=crop_margin, min_width=crop_min_width, min_height=crop_min_height,
                                           verbose=verbose)
                    if not analysis_keep_files and os.path.exists(img_out_file):
                        os.remove(img_out_file)
                return result, frame, metadata
        sleep(poll_interval)

    # clean up if necessary
    if not analysis_keep_files and os.path.exists(img_in_file):
        os.remove(img_in_file)
    if not analysis_keep_files and os.path.exists(img_out_file):
        os.remove(img_out_file)

    return False, frame, metadata


def process(input, input_type, nth_frame, max_frames, analysis_input, analysis_output, analysis_tmp,
            analysis_timeout, analysis_type, analysis_keep_files, from_frame, to_frame,
            min_score, required_labels, excluded_labels, poll_interval,
            output, output_type, output_format, output_tmp, output_fps, output_metadata,
            crop_to_content, crop_margin, crop_min_width, crop_min_height,
            verbose, progress):
    """
    Processes the input video or webcam feed.
    
    :param input: the input video or webcam ID
    :type input: str
    :param input_type: the type of input, INPUT_TYPES
    :type input_type: str
    :param nth_frame: for frame skipping to speed up processing
    :type nth_frame: int
    :param max_frames: the maximum number of processed frames before exiting (<=0 for unlimited)
    :type max_frames: int
    :param analysis_input: the input directory of the image analysis process
    :type analysis_input: str or None
    :param analysis_output: the output directory of the image analysis process
    :type analysis_output: str or None
    :param analysis_tmp: the tmp directory to write the image to before moving it into the image analysis input dir
    :type analysis_tmp: str or None
    :param analysis_timeout: the number of seconds to wait for analysis to finish before skipping frame
    :type analysis_timeout: float
    :param analysis_type: the type of output the analysis is generated, see ANALYSIS_TYPES
    :type analysis_type: str
    :param analysis_keep_files: whether to keep the analysis files rather than deleting them
    :type analysis_keep_files: bool
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
    :param poll_interval: the interval in seconds for the file polling
    :type poll_interval: float
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
    :type progress: int`
    """

    # open input
    if input_type not in INPUT_TYPES:
        raise Exception("Unknown input type: %s" % input_type)
    if input_type == INPUT_VIDEO:
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
    if (analysis_input is not None) and (analysis_output is None):
        raise Exception("No analysis output dir specified, but analysis input dir provided!")
    if (analysis_input is None) and (analysis_output is not None):
        raise Exception("No analysis input dir specified, but analysis output dir provided!")

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
    while cap.isOpened():
        # next frame
        retval, frame = cap.read()
        count += 1
        frames_count += 1

        if verbose and (frames_count % progress == 0):
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
                metadata = None

                # do we want to keep frame?
                if analysis_input is not None:
                    keep, frame, metadata = process_image(frame, frames_count, analysis_input, analysis_output, analysis_tmp,
                                                          analysis_timeout, analysis_type, analysis_keep_files, min_score,
                                                          required_labels, excluded_labels, poll_interval,
                                                          crop_to_content, crop_margin, crop_min_width, crop_min_height,
                                                          verbose)
                    if not keep:
                        continue

                frames_processed += 1

                if out is not None:
                    out.write(frame)
                else:
                    if output_tmp is not None:
                        tmp_file = os.path.join(output_tmp, output_format % frames_count)
                        out_file = os.path.join(output, output_format % frames_count)
                        cv2.imwrite(tmp_file, frame)
                        os.rename(tmp_file, out_file)
                        if metadata is not None:
                            tmp_file = os.path.splitext(tmp_file)[0] + ".yaml"
                            out_file = os.path.splitext(out_file)[0] + ".yaml"
                            with open(tmp_file, "w") as yf:
                                safe_dump(metadata, yf)
                            os.rename(tmp_file, out_file)
                    else:
                        out_file = os.path.join(output, output_format % frames_count)
                        cv2.imwrite(out_file, frame)
                        if metadata is not None:
                            out_file = os.path.splitext(out_file)[0] + ".yaml"
                            with open(out_file, "w") as yf:
                                safe_dump(metadata, yf)
        else:
            break

    if verbose:
        log("Frames processed: %d" % frames_count)

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
        prog="vfs-process",
        description="Tool for replaying videos or grabbing frames from webcam, presenting it to an image analysis "
                    + "framework to determine whether to include the frame in the output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--input", metavar="FILE_OR_ID", help="the video file to read or the webcam ID", required=True)
    parser.add_argument("--input_type", help="the input type", choices=INPUT_TYPES, required=True)
    parser.add_argument("--nth_frame", metavar="INT", help="every nth frame gets presented to the analysis process", required=False, type=int, default=10)
    parser.add_argument("--max_frames", metavar="INT", help="the maximum number of processed frames before exiting (<=0 for unlimited)", required=False, type=int, default=0)
    parser.add_argument("--from_frame", metavar="INT", help="the starting frame (incl.); ignored if <= 0", required=False, type=int, default=-1)
    parser.add_argument("--to_frame", metavar="INT", help="the last frame to process (incl.); ignored if <= 0", required=False, type=int, default=-1)
    parser.add_argument("--analysis_input", metavar="DIR", help="the input directory used by the image analysis process; if not provided, all frames get accepted", required=False)
    parser.add_argument("--analysis_tmp", metavar="DIR", help="the temporary directory to place the images in before moving them into the actual input directory (to avoid race conditions)", required=False)
    parser.add_argument("--analysis_output", metavar="DIR", help="the output directory used by the image analysis process", required=False)
    parser.add_argument("--analysis_timeout", metavar="SECONDS", help="the maximum number of seconds to wait for the image analysis to finish processing", required=False, type=float, default=10)
    parser.add_argument("--analysis_type", help="the type of output the analysis process generates", choices=ANALYSIS_TYPES, required=False, default=ANALYSIS_TYPES[0])
    parser.add_argument("--analysis_keep_files", help="whether to keep the analysis files rather than deleting them", action="store_true", required=False)
    parser.add_argument("--min_score", metavar="FLOAT", help="the minimum score that a prediction must have", required=False, type=float, default=0.0)
    parser.add_argument("--required_labels", metavar="LIST", help="the comma-separated list of labels that the analysis output must contain (with high enough scores)", required=False)
    parser.add_argument("--excluded_labels", metavar="LIST", help="the comma-separated list of labels that the analysis output must not contain (with high enough scores)", required=False)
    parser.add_argument('--poll_interval', type=float, help='interval in seconds for polling for result files', required=False, default=0.1)
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
    parser.add_argument("--progress", metavar="INT", help="every nth frame a progress is being output (in verbose mode)", required=False, type=int, default=100)
    parser.add_argument("--verbose", help="for more verbose output", action="store_true", required=False)
    parsed = parser.parse_args(args=args)

    # parse labels
    required_labels = None
    if parsed.required_labels is not None:
        required_labels = parsed.required_labels.split(",")
    excluded_labels = None
    if parsed.excluded_labels is not None:
        excluded_labels = parsed.excluded_labels.split(",")

    process(input=parsed.input, input_type=parsed.input_type, nth_frame=parsed.nth_frame, max_frames=parsed.max_frames,
            analysis_input=parsed.analysis_input, analysis_output=parsed.analysis_output,
            analysis_tmp=parsed.analysis_tmp, analysis_timeout=parsed.analysis_timeout,
            analysis_type=parsed.analysis_type, analysis_keep_files=parsed.analysis_keep_files,
            from_frame=parsed.from_frame, to_frame=parsed.to_frame,
            min_score=parsed.min_score, required_labels=required_labels, excluded_labels=excluded_labels,
            poll_interval=parsed.poll_interval,
            output=parsed.output, output_type=parsed.output_type, output_format=parsed.output_format,
            output_tmp=parsed.output_tmp, output_fps=parsed.output_fps, output_metadata=parsed.output_metadata,
            crop_to_content=parsed.crop_to_content, crop_margin=parsed.crop_margin,
            crop_min_width=parsed.crop_min_width, crop_min_height=parsed.crop_min_height,
            verbose=parsed.verbose, progress=parsed.progress)


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

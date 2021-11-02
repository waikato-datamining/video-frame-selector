import os

from vfs.logging import log
from vfs.predictions import load_roiscsv, load_opexjson

IMAGE_EXTENSIONS = [".jpg", ".png"]
""" the supported image types. """

INPUT_IMAGE_DIR = "image_dir"
INPUT_VIDEO = "video"
INPUT_WEBCAM = "webcam"
INPUT_TYPES = [INPUT_IMAGE_DIR, INPUT_VIDEO, INPUT_WEBCAM]
""" The available input types. """

ANALYSIS_ROISCSV = "rois_csv"
ANALYSIS_OPEXJSON = "opex_json"
ANALYSIS_TYPES = [ANALYSIS_ROISCSV, ANALYSIS_OPEXJSON]
""" The available analysis file types. """

OUTPUT_JPG = "jpg"
OUTPUT_MJPG = "mjpg"
OUTPUT_TYPES = [OUTPUT_JPG, OUTPUT_MJPG]
""" The available output types. """

ANALYSIS_FORMAT = "%06d.EXT"
""" The file name format to use for the image analysis framework. """


def list_images(image_path, verbose=False):
    """
    Lists the images in the specified directory and returns a sorted list of
    absolute file names.

    :param image_path: the directory to scan for images
    :type image_path: str
    :param verbose: whether to be verbose
    :type verbose: bool
    :return: the list of absolute file names
    :rtype: list
    """
    result = []
    if verbose:
        log("Looking for images in: %s" % image_path)
    for f in os.listdir(image_path):
        full = os.path.join(image_path, f)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(full)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        result.append(full)
    result.sort()
    if verbose:
        log("# of images found: %d" % len(result))
    return result

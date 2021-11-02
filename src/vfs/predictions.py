import csv
import io
from vfs.logging import log
from opex import ObjectPredictions


class Prediction(object):
    """
    Encapsulates a single prediction.
    """

    def __init__(self, index, label, score, data=None, coords=None):
        """
        Initializes the prediction.

        :param index: the 0-based index of the prediction
        :type index: int
        :param label: the label string
        :type label: str
        :param score: the prediction score
        :type score: float
        :param data: additional, optional data
        :type data: object
        :param coords: the (x0, y0, x1, y1) coordinates
        :type coords: tuple
        """
        self.index = index
        self.label = label
        self.score = score
        self.data = data
        self.coords = coords

    def __str__(self):
        """
        Returns a string representation of the object.

        :return: the string representation
        :rtype: str
        """
        return "%d: %s = %f" % (self.index, self.label, self.score)


def _load_roiscsv(fp):
    """
    Loads the specified ROIs CSV file.

    :param fp: the file object for the ROIs CSV data to load
    :type fp: file
    :return: the list of predictions
    :rtype: list
    """
    result = []

    reader = csv.DictReader(fp)
    for i, row in enumerate(reader):
        # score
        score = 1.0
        if "score" in row:
            score = float(row["score"])

        # label
        label = ""
        if "label_str" in row:
            label = row["label_str"]

        # coordinates
        coords = None
        if "x0" in row:
            coords = (int(float(row["x0"])), int(float(row["y0"])), int(float(row["x1"])), int(float(row["y1"])))
        if "x" in row:
            x = int(float(row["x"]))
            y = int(float(row["y"]))
            coords = (x, y, x + int(float(row["w"])) - 1, y + int(float(row["h"])) - 1)

        p = Prediction(i, label, score, coords=coords)
        result.append(p)

    return result


def load_roiscsv(analysis_file):
    """
    Loads the specified ROIs CSV file.

    :param analysis_file: the ROIs CSV file to load
    :type analysis_file: str
    :return: the list of predictions
    :rtype: list
    """
    with open(analysis_file, "r") as fp:
        return _load_roiscsv(fp)


def load_roiscsv_from_str(analysis_str):
    """
    Loads data from the specified ROIs CSV string.

    :param analysis_str: the ROIs CSV string to parse
    :type analysis_str: str or bytes
    :return: the list of predictions
    :rtype: list
    """
    if isinstance(analysis_str, bytes):
        analysis_str = analysis_str.decode()
    return _load_roiscsv(io.StringIO(analysis_str))


def _opex_to_predictions(preds):
    """
    Turns the OPEX data structure into predictions.

    :param preds: the OPEX data to convert
    :type preds: ObjectPredictions
    :return: the list of predictions
    :rtype: list
    """
    result = []

    for i, pred in enumerate(preds.objects):
        coords = (pred.bbox.left, pred.bbox.top, pred.bbox.bottom, pred.bbox.right)
        p = Prediction(i, pred.label, pred.score, coords=coords)
        result.append(p)

    return result


def load_opexjson(analysis_file):
    """
    Loads the specified OPEX JSON file.

    :param analysis_file: the OPEX JSON file to load
    :type analysis_file: str
    :return: the list of predictions
    :rtype: list
    """
    return _opex_to_predictions(ObjectPredictions.load_json_from_file(analysis_file))


def load_opexjson_from_str(analysis_str):
    """
    Loads the specified OPEX JSON string.

    :param analysis_str: the OPEX JSON string to load
    :type analysis_str: str or bytes
    :return: the list of predictions
    :rtype: list
    """
    if isinstance(analysis_str, bytes):
        analysis_str = analysis_str.decode()
    return _opex_to_predictions(ObjectPredictions.from_json_string(analysis_str))


def crop_frame(frame, predictions, metadata, margin=0, min_width=2, min_height=2, verbose=False):
    """
    Crops the frame according to the content of the predictions.
    If even only a single predictions has no predictions, then no cropping occurs.

    :param frame: the frame to crop
    :type frame: ndarray
    :param predictions: the list of Prediction objects, can be None
    :type predictions: list
    :param metadata: for attaching metadata
    :type metadata: dict
    :param margin: the margin around the cropped content
    :type margin: int
    :param min_width: the minimum width for the cropped content
    :type min_width: int
    :param min_height: the minimum height for the cropped content
    :type min_height: int
    :param verbose: whether to print logging information
    :type verbose: bool
    :return: the (potentially) cropped frame
    :rtype: ndarray
    """

    height, width = frame.shape[:2]
    metadata["frame"] = {
        "width": width,
        "height": height,
    }

    if predictions is None:
        return frame

    if verbose:
        log("Frame width x height: %d x %d" % (width, height))

    x0 = width
    y0 = height
    x1 = 0
    y1 = 0

    for p in predictions:
        if p.coords is None:
            continue
        cx0, cy0, cx1, cy1 = p.coords
        x0 = min(x0, cx0)
        y0 = min(y0, cy0)
        x1 = max(x1, cx1)
        y1 = max(y1, cy1)

    # no crop window found, cannot crop
    if (x0 == width) or (y0 == height):
        if verbose:
            log("Cannot crop")
        metadata["cropped"] = False
        return frame

    metadata["cropped"] = True
    metadata["minimal_bbox"] = {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
    }

    # add margin?
    if margin > 0:
        x0 = max(0, x0 - margin)
        y0 = max(0, y0 - margin)
        x1 = min(width - 1, x1 + margin)
        y1 = min(height - 1, y1 + margin)
        metadata["margin_bbox"] = {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
        }

    # correct width?
    curr_width = x1 - x0 + 1
    if curr_width < min_width:
        if verbose:
            log("Width below min_width: %d < %d" % (curr_width, min_width))
            log("Current: x0=%d, x1=%d" % (x0, x1))
        inc = (min_width - curr_width) // 2
        x0 = max(0, x0 - inc)
        x1 = min(width - 1, x0 + min_width)
        if verbose:
            log("Corrected: x0=%d, x1=%d" % (x0, x1))

    # correct height?
    curr_height = y1 - y0 + 1
    if curr_height < min_height:
        if verbose:
            log("Height below min_height: %d < %d" % (curr_height, min_height))
            log("Current: y0=%d, y1=%d" % (y0, y1))
        inc = (min_height - curr_height) // 2
        y0 = max(0, y0 - inc)
        y1 = min(height - 1, y0 + min_height)
        if verbose:
            log("Corrected: y0=%d, y1=%d" % (y0, y1))

    metadata["crop_bbox"] = {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
    }

    if verbose:
        log("Cropping: x0=%d, y0=%d, x1=%d, y1=%d" % (x0, y0, x1, y1))
    return frame[y0:y1, x0:x1]


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

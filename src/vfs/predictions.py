import csv
import sys
from vfs.logging import log


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


def load_roiscsv(analysis_file):
    """
    Loads the specified ROIs CSV file.

    :param analysis_file: the ROIs CSV file to check
    :type analysis_file: str
    :return: the list of predictions
    :rtype: list
    """
    result = []

    with open(analysis_file) as cf:
        reader = csv.DictReader(cf)
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
                coords = (int(row["x0"]), int(row["y0"]), int(row["x1"]), int(row["y1"]))
            if "x" in row:
                x = int(row["x"])
                y = int(row["y"])
                coords = (x, y, x + int(row["w"]) - 1, y + int(row["h"]) - 1)

            p = Prediction(i, label, score, coords=coords)
            result.append(p)

    return result


def crop_frame(frame, predictions, verbose):
    """
    Crops the frame according to the content of the predictions.
    If even only a single predictions has no predictions, then no cropping occurs.

    :param frame: the frame to crop
    :type frame: ndarray
    :param predictions: the list of Prediction objects, can be None
    :type predictions: list
    :param verbose: whether to print logging information
    :type verbose: bool
    :return: the (potentially) cropped frame
    :rtype: ndarray
    """

    if predictions is None:
        return frame

    x0 = sys.maxsize
    y0 = sys.maxsize
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

    if (x0 == sys.maxsize) or (y0 == sys.maxsize):
        if verbose:
            log("Cannot crop")
        return frame
    else:
        if verbose:
            log("Cropping: x0=%d, y0=%d, x1=%d, y1=%d" % (x0, y0, x1, y1))
        return frame[y0:y1, x0:x1]

import cv2


def diff_img(img1, img2):
    """
    Computes the absolute difference between two images.

    :param img1: the first image
    :param img2: the second image
    """
    return cv2.absdiff(img1, img2)


def to_bw(img, threshold):
    """
    Turns the gray image into binary.

    :param img: the image to convert
    :param threshold: the threshold to use
    :type threshold: int
    :return: the binary image
    """
    thresh, binary = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
    return binary


def count_diff(img):
    """
    Counts the non-zero pixels in the image.

    :param img: the image to process
    :return: the count
    :rtype: int
    """
    return cv2.countNonZero(img)


def detect_change(img1, img2, bw_threshold, change_threshold):
    """
    Returns true if there was change detected between the two images (turns them into gray images first).

    :param img1: the first image
    :param img2: the second image
    :param bw_threshold: the black/white threshold (0-255)
    :type bw_threshold: int
    :param change_threshold: the threshold for changes (0-1)
    :type change_threshold: float
    :return: the detected ratio, whether change was detected
    :rtype threshold: (float, bool)
    """
    size = img1.size
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    count = count_diff(to_bw(diff_img(img1, img2), bw_threshold))
    ratio = float(count) / float(size)
    return ratio, ratio > change_threshold

from datetime import datetime


def log(*args):
    """
    Just outputs the arguments with a timestamp.

    :param args: the arguments to log
    """
    print(*("%s - " % str(datetime.now()), *args))

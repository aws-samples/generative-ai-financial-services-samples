import sys
import logging
import datetime
from parameters.parameters import log_files_dict

timestamp_string = datetime.datetime.now().strftime("%Y-%m-%d")
textract_log = log_files_dict["textract_log"]
formatter = logging.Formatter(
    "%(asctime)s: %(levelname)s [line: %(lineno)d, sourcefile: %(name)s'] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    return console_handler


def get_file_handler():
    file_handler = logging.FileHandler(textract_log)
    file_handler.setFormatter(formatter)
    return file_handler


def get_logger(logger_name):
    activities_logger = logging.getLogger(logger_name)
    if not activities_logger.handlers:
        # Define logger file handler and set formatter
        activities_logger.setLevel(logging.DEBUG)
        activities_logger.addHandler(get_console_handler())
        activities_logger.addHandler(get_file_handler())
        activities_logger.propagate = False
    return activities_logger

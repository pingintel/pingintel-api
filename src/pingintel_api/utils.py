import time, logging
from timeit import default_timer as timer

import click
import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


def raise_for_status(response: requests.Response):
    if response.ok:
        return

    error_msg = response.text
    logger.error(f"{response.status_code} {response.reason}: {error_msg}")

    raise HTTPError(error_msg, response=response)


def is_fileobj(source):
    return hasattr(source, "read")


def set_verbosity(verbose):
    # print("set_verbosity", verbose, settings.IS_SERVER_ENV)

    console = logging.StreamHandler()
    consoleformat = "%(asctime)s %(levelname)-7s %(message)s [%(name)s:%(lineno)s %(funcName)s]"
    consoleformatter = logging.Formatter(consoleformat, datefmt="%H:%M:%S")
    console.setFormatter(consoleformatter)

    handlers = []
    handlers.append(console)

    WARNING_ONLY_LOGGERS = [
        "urllib3.connectionpool",
        "urllib3.util.retry",
        "requests.packages.urllib3.connectionpool",
        "requests.packages.urllib3.util.retry",
    ]

    DEFAULT_VERBOSITY = 0
    keep_subloggers = False
    if verbose == DEFAULT_VERBOSITY - 1:
        base_level = logging.ERROR
    elif verbose == DEFAULT_VERBOSITY:
        base_level = logging.WARNING
    elif verbose == DEFAULT_VERBOSITY + 1:
        base_level = logging.INFO
    elif verbose == DEFAULT_VERBOSITY + 2:
        base_level = logging.DEBUG
    else:
        keep_subloggers = True
        base_level = logging.DEBUG

    logging.basicConfig(level=base_level, handlers=handlers, force=True)

    if not keep_subloggers:
        for logname in WARNING_ONLY_LOGGERS:
            logging.getLogger(logname).setLevel(logging.WARNING)

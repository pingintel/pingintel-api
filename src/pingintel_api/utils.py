import time
from timeit import default_timer as timer

import click
import requests
from requests.exceptions import HTTPError

global start_time
start_time = None


def log(msg):
    global start_time
    if start_time is None:
        start_time = timer()
    elapsed = timer() - start_time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"[{timestamp} T+{elapsed:.1f}s] {msg}")


def raise_for_status(response: requests.Response):
    if response.ok:
        return

    error_msg = response.text
    log(f"{response.status_code} {response.reason}: {error_msg}")

    raise HTTPError(error_msg, response=response)


def is_fileobj(source):
    return hasattr(source, "read")

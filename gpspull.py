#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Retrieve GPS files."""

import argparse
from datetime import timedelta, date, datetime
import json
import logging
import os
import re
from time import mktime
import time
from humanize import naturalsize
import sys
import socket
import struct
import dateutil.parser  # aka python-dateutil
import pycurl
import pathlib
from ruamel.yaml import YAML
from urllib.parse import urlparse
import errno

START_TIME = None
PULL_JOB = os.environ['PULL_JOB']
BASE_DIR = os.environ['BASE_DIR']
WINDOW_SIZE_FACTOR = 2

def parse_config():
    config_file = pathlib.Path(BASE_DIR)
    config_file /= "config"
    config_file /= (PULL_JOB + ".yml")
    logging.debug("Parsing config file. (%s)", config_file)

    yaml = YAML()
    config = yaml.load(config_file)

    return config


def setRecvSpeed(curl, speed):
    def sockoptfunction(curlfd, purpose):
        logging.debug("Setting RECV_SPEED to %s b/s", speed)
        sock = socket.socket(fileno=curlfd)

        window_size = speed * WINDOW_SIZE_FACTOR
        if sys.maxsize > 2 ** 32:
            size = struct.pack(str("ll"), int(window_size), int(0))
        else:
            size = struct.pack(str("ii"), int(window_size), int(0))

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
        sock.detach()
        return 0

    curl.setopt(curl.SOCKOPTFUNCTION, sockoptfunction)
    curl.setopt(curl.MAX_RECV_SPEED_LARGE, speed)


def poll(receiver, day):
    c = pycurl.Curl()
    c.setopt(c.VERBOSE, True)
    if 'userpw' in receiver:
        c.setopt(pycurl.USERPWD, receiver['userpw'])

    if 'recvSpeed' in receiver:
        setRecvSpeed(c, receiver['recvSpeed'])

    url = day.strftime(receiver['url']) % receiver
    c.setopt(c.URL, url)

    url_parts = urlparse(url)
    out_base = pathlib.Path(BASE_DIR) / receiver['station']
    try:
        out_dir = out_base / os.path.dirname(url_parts.path)[1:]
        os.makedirs(out_dir)
        logging.info("Created %s", out_dir)

    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    out_file = out_base / url_parts.path[1:]

    if os.path.exists(out_file):
        logging.info("Finished with %s. I already have %s",
                     receiver['station'], out_file)
        return True

    logging.info("Fetching %s from %s", out_file, url)
    try:
        tmp_file = str(out_file) + ".tmp"
        with open(tmp_file, 'wb') as f:
            c.setopt(c.WRITEDATA, f)
            c.perform()
            os.rename(tmp_file, out_file)
    except:
        os.remove(out_file)
        return True

    return False


def main():
    """Where it all begins."""

    logging.basicConfig(level=logging.DEBUG)
    logging.debug("BASE_DIR: %s", BASE_DIR)
    logging.debug("PULL_JOB: %s", PULL_JOB)

    config = parse_config()

    day = datetime.datetime.utcnow().date()
    receivers = config['receivers']

    while receivers:
        day -= timedelta(1)
        for receiver in config['receivers']:
            finished = poll(receiver, day)
            if finished:
                receivers.remove(receiver)


if __name__ == '__main__':
    main()

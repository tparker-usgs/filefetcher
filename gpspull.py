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

WINDOW_SIZE_FACTOR = 2

def parse_config(config_file):
    logging.debug("Parsing config file. [%s]", config_file)

    yaml = YAML()
    try:
        config = yaml.load(config_file)
    except FileNotFoundError:
        logging.error("Cannot read config file %s", config_file)
        exit(1)

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
    out_base = pathlib.Path(receiver['out_dir']) / receiver['station']
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
        try:
            os.remove(out_file)
        except FileNotFoundError:
            pass
        return True

    return False


def get_env_var(var):
    if var in os.environ:
        logging.debug("%s: %s", var, os.environ[var])
        return os.environ[var]

    else:
        print("Envionment variable {} not set, exiting.".format(var))
        sys.exit(1)


def validate_env():
    env = {}
    env['config_file'] = get_env_var('CONFIG_FILE')

    return env


def get_backfill_date(config):
    if 'backfill' not in config:
        return None

    backfill = datetime.strptime(config['backfill'], '%m/%d/%Y')
    logging.debug("Backfill date: %s", backfill)

    return backfill

def main():
    """Where it all begins."""

    logging.basicConfig(level=logging.DEBUG)
    env = validate_env()
    config = parse_config(pathlib.Path(env['config_file']))

    day = datetime.utcnow().date()
    receivers = config['receivers']
    backfill_date = get_backfill_date(config)

    while receivers:
        day -= timedelta(1)
        for receiver in config['receivers']:
            finished = poll(receiver, day)

            if backfill_date:
                finished = day <= backfill_date

            if finished:
                receivers.remove(receiver)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Retrieve GPS files."""

from datetime import timedelta, datetime
import logging
import os
import sys
import socket
import struct
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
    except OSError as e:
        if e.errno == errno.EEXIST:
            logging.error("Cannot read config file %s", config_file)
            exit(1)
        else:
            raise

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
    finished = False
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
        logging.info("I already have %s", out_file)
        finished = True
    else:
        logging.info("Fetching %s from %s", out_file, url)
        try:
            tmp_file = str(out_file) + ".tmp"
            with open(tmp_file, 'wb') as f:
                c.setopt(c.WRITEDATA, f)
                c.perform()
                os.rename(tmp_file, out_file)
        except Exception as e1:
            logging.error("Unexpected error while retrieving file, lets set this one aside.", e1)
            try:
                os.remove(out_file)
            except OSError as e2:
                if e2.errno != errno.EEXIST:
                    raise
            return True

    if 'backfill' in receiver:
        backfill_date = datetime.strptime(receiver['backfill'], '%m/%d/%Y').date()
        if day > backfill_date:
            logging.info("Continuing to backfill from %s to %s", day, backfill_date)
            finished = False
        else:
            logging.debug("Continuing to backfill from %s to %s", day, backfill_date)

    return finished


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


def main():
    """Where it all begins."""

    logging.basicConfig(level=logging.DEBUG)
    env = validate_env()
    config = parse_config(pathlib.Path(env['config_file']))

    day = datetime.utcnow().date()
    receivers = config['receivers']

    while receivers:
        day -= timedelta(1)
        for receiver in config['receivers']:
            finished = poll(receiver, day)

            if finished:
                logging.info("All done with %s", receiver['station'])
                receivers.remove(receiver)

    logging.info("That's evething, I'm done for the day.")

if __name__ == '__main__':
    main()

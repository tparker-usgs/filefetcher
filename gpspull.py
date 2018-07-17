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
import ruamel.yaml
from urllib.parse import urlparse
import errno
from multiprocessing import Process
from buffering_smtp_handler import BufferingSMTPHandler

WINDOW_SIZE_FACTOR = 2

env = None


def exit_with_error(error):
    logger.error(error)
    logging.shutdown()
    sys.exit(1)


def parse_config():
    config_file = pathlib.Path(os.environ['CONFIG_FILE'])
    logger.debug("Parsing config file. [%s]", config_file)

    yaml = ruamel.yaml.YAML()
    try:
        config = yaml.load(config_file)
    except ruamel.yaml.parser.ParserError as e1:
        logger.error("Cannot parse config file")
        exit_with_error(e1)
    except OSError as e:
        if e.errno == errno.EEXIST:
            logger.error("Cannot read config file %s", config_file)
            exit_with_error(e)
        else:
            raise

    global global_config
    global_config = config


def setRecvSpeed(curl, speed):
    if speed < 1:
        return

    def sockoptfunction(curlfd, purpose):
        logger.debug("Setting RECV_SPEED to %s b/s", speed)
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
        logger.info("Created %s", out_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    out_file = out_base / url_parts.path[1:]
    if os.path.exists(out_file):
        logger.info("I already have %s", out_file)
        finished = True
    else:
        logger.info("Fetching %s from %s", out_file, url)
        try:
            tmp_file = str(out_file) + ".tmp"
            with open(tmp_file, 'wb') as f:
                c.setopt(c.WRITEDATA, f)
                c.perform()
                os.rename(tmp_file, out_file)
        except Exception:
            msg = "Unexpected error while retrieving file, " \
                  + "lets set this one aside."
            logger.error(msg)
            try:
                os.remove(out_file)
            except OSError as e2:
                if e2.errno != errno.ENOENT:
                    raise
            return True

    if 'backfill' in receiver:
        backfill_date = datetime.strptime(receiver['backfill'], '%m/%d/%Y')
        backfill_date = backfill_date.date()
        if day > backfill_date:
            logger.info("Continuing to backfill from %s to %s", day,
                        backfill_date)
            finished = False
        else:
            logger.debug("Continuing to backfill from %s to %s", day,
                         backfill_date)

    return finished


def get_env_var(var, required=False):
    if var in os.environ:
        logger.debug("%s: %s", var, os.environ[var])
        return os.environ[var]

    else:
        if required:
            msg = "Envionment variable {} not set, exiting.".format(var)
            exit_with_error(EnvironmentError(msg))


def poll_network(config):
    day = datetime.utcnow().date()
    receivers = config['receivers']
    while receivers:
        day -= timedelta(1)
        for receiver in config['receivers']:
            finished = poll(receiver, day)

            if finished:
                logger.info("All done with receiver %s.", receiver['station'])
                receivers.remove(receiver)

    logger.info("All done with network %s.", config['name'])


def setup_logging():
    global logger
    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    logger.addHandler(ch)

    try:
        subject = "gpspull logs"
        handler = BufferingSMTPHandler(os.environ['MAILHOST'],
                                       os.environ['SENDER'],
                                       os.environ['RECIPIENT'], subject, 1000,
                                       "%(levelname)s - %(message)s")
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
    except KeyError:
        logger.info("SMTP logging not configured.")


def main():
    """Where it all begins."""

    setup_logging()

    try:
        parse_config()
    except KeyError:
        exit_with_error("Environment variable CONFIG_FILE not set, exiting.")

    procs = []
    for network in global_config['networks']:
        if 'disabled' in network and network['disabled']:
            logger.info("Network %s is disabled, skiping it.", network['name'])
        else:
            p = Process(target=poll_network, args=(network,))
            procs.append(p)
            p.start()

    for proc in procs:
        proc.join()

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

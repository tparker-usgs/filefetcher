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
from string import Template
import signal
import logging
import os
import sys
import socket
import struct
import pathlib
from urllib.parse import urlparse
import errno
from multiprocessing import Process

import ruamel.yaml
import tomputils.util as tutil
import pycurl
import humanize
import multiprocessing_logging


REQ_VERSION = (3, 0)
WINDOW_SIZE_FACTOR = 2
CONFIG_FILE_ENV = 'FF_CONFIG_FILE'
MAX_UPDATE_FREQ = timedelta(seconds=10)
PYCURL_MINOR_ERRORS = [pycurl.E_COULDNT_CONNECT, pycurl.E_OPERATION_TIMEDOUT,
                       pycurl.E_FAILED_INIT, pycurl.E_REMOTE_FILE_NOT_FOUND]
START_TIME = datetime.now()


def parse_config():
    config_file = pathlib.Path(tutil.get_env_var(CONFIG_FILE_ENV))
    yaml = ruamel.yaml.YAML()
    try:
        global_config = yaml.load(config_file)
    except ruamel.yaml.parser.ParserError as e1:
        logger.error("Cannot parse config file")
        tutil.exit_with_error(e1)
    except OSError as e:
        if e.errno == errno.EEXIST:
            logger.error("Cannot read config file %s", config_file)
            tutil.exit_with_error(e)
        else:
            raise
    return global_config


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


def backfill_finished(datalogger, day):
    if 'backfill' not in datalogger:
        return True

    backfill_date = datetime.strptime(datalogger['backfill'], '%m/%d/%Y')
    backfill_date = backfill_date.date()
    if day > backfill_date:
        logger.debug("Continuing to backfill from %s to %s", day,
                     backfill_date)
        return False
    else:
        logger.info("Completed backfill from %s to %s", day, backfill_date)
        return True


def create_curl(datalogger, url):
    c = pycurl.Curl()
    c.setopt(c.VERBOSE, True)
    if 'userpwd' in datalogger:
        userpwd = tutil.get_env_var(datalogger['userpwd'], secret=True)
        logger.debug("Setting userpw to whatever is in $%s",
                     datalogger['userpwd'])
        c.setopt(pycurl.USERPWD, userpwd)

    if 'recvSpeed' in datalogger:
        setRecvSpeed(c, datalogger['recvSpeed'])

    if 'port' in datalogger:
        c.setopt(pycurl.PORT, datalogger['port'])

    last_update = datetime.now()

    def progress(download_t, download_d, upload_t, upload_d):
        nonlocal last_update
        now = datetime.now()
        if now > last_update + MAX_UPDATE_FREQ:
            download_d_str = humanize.naturalsize(download_d, format='%.2f')
            download_t_str = humanize.naturalsize(download_t, format='%.2f')
            logger.debug("Downloaded %s of %s", download_d_str, download_t_str)
            last_update = now
        return 0

    c.setopt(c.NOPROGRESS, False)
    c.setopt(c.XFERINFOFUNCTION, progress)
    c.setopt(c.URL, url)

    return c


def make_out_dir(dir):
    try:
        os.makedirs(dir)
        logger.info("Created %s", dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def remove_file(file):
    try:
        os.remove(file)
    except OSError as e2:
        if e2.errno != errno.ENOENT:
            raise


def fetch_file(c, out_file):
    tmp_dir = tutil.get_env_var("FF_TMP_DIR", default=".")
    tmp_file = "{}.tmp".format(os.path.basename(out_file))
    tmp_path = pathlib.Path(tmp_dir) / tmp_file

    try:
        with open(tmp_path, 'wb') as f:
            c.setopt(c.WRITEDATA, f)
            c.perform()
            make_out_dir(os.path.dirname(out_file))
            os.rename(tmp_path, out_file)
    except pycurl.error as e:
        if e.args[0] in PYCURL_MINOR_ERRORS:
            logger.info("Error retrieving %s: %s", out_file, e)
        else:
            logger.exception("Error retrieving %s", out_file)
        remove_file(tmp_path)
        return True

    return False


def find_out_file(datalogger, day, url):
    if 'out_path' in datalogger:
        out_str = Template(datalogger['out_path']).substitute(datalogger)
        out_path = day.strftime(out_str)
    else:
        url_parts = urlparse(url)
        out_path = pathlib.Path(datalogger['name']) / url_parts.path[1:]

    return pathlib.Path(datalogger['out_dir']) / out_path


def poll_logger(datalogger, day):
    if 'disabled' in datalogger and datalogger['disabled']:
        logger.debug("Skipping %s (disabled)", datalogger['name'])
        return True

    url_str = Template(datalogger['url']).substitute(datalogger)
    url = day.strftime(url_str)
    out_path = find_out_file(datalogger, day, url)
    if os.path.exists(out_path):
        logger.info("I already have %s", out_path)
        finished = True
    else:
        logger.info("Fetching %s from %s", out_path, url)
        c = create_curl(datalogger, url)
        finished = fetch_file(c, out_path)

    run_time = datetime.now() - START_TIME
    time_exceeded = run_time > timedelta(minutes=global_config['maxRunTime'])
    if time_exceeded:
        logger.info("maxRunTime exceeded, lets cleanup and exit.")
    return time_exceeded or (finished and backfill_finished(datalogger, day))


def poll_loggers(dataloggers, day):
    for datalogger in dataloggers:
        finished = poll_logger(datalogger, day)

        if finished:
            logger.info("All done with logger %s.", datalogger['name'])
            dataloggers.remove(datalogger)


def poll_queue(config):
    try:
        day = datetime.utcnow().date()
        dataloggers = config['dataloggers']
        while dataloggers:
            day -= timedelta(1)
            poll_loggers(dataloggers, day)
    finally:
        logger.info("All done with queue %s.", config['name'])
        for handler in logger.handlers:
            handler.flush()


def poll_queues():
    procs = []
    for queue in global_config['queues']:
        if 'disabled' in queue and queue['disabled']:
            logger.info("Queue %s is disabled, skiping it.", queue['name'])
        else:
            p = Process(target=poll_queue, args=(queue,))
            procs.append(p)
            p.start()

    return procs


def main():
    # let ctrl-c work as it should.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    global logger
    logger = tutil.setup_logging("filefetcher errors")
    multiprocessing_logging.install_mp_handler()

    msg = "Python interpreter is too old. I need at least {} " \
          + "for EmailMessage.iter_attachments() support."
    tutil.enforce_version(REQ_VERSION, msg.format(REQ_VERSION))

    try:
        global global_config
        global_config = parse_config()
    except KeyError:
        msg = "Environment variable %s unset, exiting.".format(CONFIG_FILE_ENV)
        tutil.exit_with_error(msg)

    procs = poll_queues()
    for proc in procs:
        proc.join()

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

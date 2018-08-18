#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Reorganise files to accomodate a new out_path. Cannot be used to
    acoommodate a changed out_path. """

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
import tomputils.util as tutil

global global_config

def parse_config():
    config_file = pathlib.Path(tutil.get_env_var('FF_CONFIG_FILE'))
    yaml = ruamel.yaml.YAML()
    global global_config
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


def process_logger(datalogger):
    os.chdir(datalogger['out_dir'])
    src_path = pathlib.Path(datalogger['name'])
    old_format = os.path.join(datalogger['name'],
                              datalogger['url'].split('/', 3)[3])
    logger.debug("Processing logger %s with format %s", datalogger['name'],
                 old_format)
    for root, dirs, files in os.walk(src_path):
        for file in files:
            try:
                date = datetime.strptime(file, old_format)
            except ValueError:
                continue
            logger.debug("Found %s date %s", file, date)

def main():
    global logger
    logger = tutil.setup_logging("urltooutpath errors")

    try:
        parse_config()
    except KeyError:
        msg = "Environment variable FF_CONFIG_FILE not set, exiting."
        tutil.exit_with_error(msg)

    for queue in global_config['queues']:
        try:
            for datalogger in queue['dataloggers']:
                process_logger(datalogger)
        finally:
            logger.info("All done with queue %s.", queue['name'])

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

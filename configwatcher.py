#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Watch config file for changes."""

import os
import difflib
import shutil
import logging

import tomputils.util as tutil


def main():
    global logger
    logger = tutil.setup_logging("FILEFETCHER CONFIGURATION CHANGED")

    config_path = tutil.get_env_var('FF_CONFIG_FILE')
    copy_path = os.path.join('/tmp', os.path.basename(config_path))

    try:
        with open(config_path, "r") as f:
            config = list(f)

        with open(copy_path, "r") as f:
            copy = list(f)

        result = difflib.unified_diff(copy, config, fromfile=copy_path,
                                      tofile=config_path)
        diff = list(result)
        if len(diff) > 0:
            shutil.copyfile(config_path, copy_path)
            logger.error("Configfile has changed.")
            logger.error("\n" + "".join(diff))
        else:
            logger.info("Configfile has not changed.")
    except FileNotFoundError:
        logger.error("Container restarted, cannot verify config.")
        shutil.copyfile(config_path, copy_path)

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

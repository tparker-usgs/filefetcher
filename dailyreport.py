#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Email a report of daily file changes."""

import os
import logging
import pathlib
import subprocess
from string import Template
from datetime import timedelta, datetime
from jinja2 import Template as jinjatmpl
import tomputils.util as tutil


REQ_VERSION = (3, 5)
CONFIG_FILE_ENV = 'FF_CONFIG'
EMAIL_TEMPLATE = """
<HTML>
{% block body %}
  <ul>
  {% for queue in queues %}
    <li>{{ queue.name }}</li>
  {% endfor %}
  </ul>
{% endblock %}
</HTML>
"""


def get_daily_total(config):
    dir = os.path.join(config['out_dir'], config['name'])
    result = subprocess.run(['find', dir, '-type', 'f', '-mtime', '-1',
                             '-print'], stdout=subprocess.PIPE)

    if result.stdout:
        return len(result.stdout.decode('utf-8').split("\n"))
    else:
        return 0


def get_coverage(config):
    if 'out_path' not in config:
        return None

    coverage = {'week': 0, 'month': 0}
    day = datetime.utcnow().date()
    week_ago = day - timedelta(7)
    month_ago = day - timedelta(30)
    while day > month_ago:
        day -= timedelta(1)
        out_str = Template(config['out_path']).substitute(config)
        out_path = day.strftime(out_str)
        file = os.path.join(config['out_dir'], out_path)
        if os.path.exists(file):
            coverage['month'] += 1
            if day > week_ago:
                coverage['week'] += 1

    return coverage


def process_datalogger(config):
    logger_results = {}
    logger_results['name'] = config['name']
    if 'disabled' in config and config['disabled']:
        logger.debug("Skipping %s (disabled)", config['name'])
        logger_results['disabled'] = True
        return logger_results

    logger_results['daily_total'] = get_daily_total(config)
    logger.debug("%s daily total: %d", config['name'],
                 logger_results['daily_total'])
    logger_results['coverage'] = get_coverage(config)

    return logger_results


def process_queue(config):
    queue = []
    for datalogger in config['dataloggers']:
        logger_results = queue.append(process_datalogger(datalogger))
        if logger_results is not None:
            queue.append(logger_results)

    return queue


def process_queues(config):
    queues = []
    for queue in config['queues']:
        if 'disabled' in queue and queue['disabled']:
            logger.info("Queue %s is disabled, skiping it.", queue['name'])
        else:
            queues.append(process_queue(queue))

    return queues


def main():
    global logger
    logger = tutil.setup_logging("filefetcher errors")

    msg = "Python interpreter is too old. I need at least {} " \
          + "for EmailMessage.iter_attachments() support."
    tutil.enforce_version(REQ_VERSION, msg.format(REQ_VERSION))

    try:
        config_file = pathlib.Path(tutil.get_env_var(CONFIG_FILE_ENV))
        config = tutil.parse_config(config_file)
    except KeyError:
        msg = "Environment variable %s unset, exiting.".format(CONFIG_FILE_ENV)
        tutil.exit_with_error(msg)

    queues = process_queues(config)
    logger.debug("Queues: %s", queues)
    tmpl = jinjatmpl(EMAIL_TEMPLATE)
    logger.debug(tmpl)
    email = tmpl.render(queues=queues)
    logger.debug(email)
    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

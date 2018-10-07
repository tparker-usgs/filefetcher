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
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

REQ_VERSION = (3, 5)
CONFIG_FILE_ENV = 'FF_CONFIG'
STYLE = {'table': """
                border-collapse:collapse;
                border-spacing:0;
                border-color:#aaa;
        """,
         'header_cell': """
                font-family:Arial, sans-serif;
                font-size:14px;
                font-weight:normal;
                padding:10px 5px;
                border-style:solid;
                border-width:0px;
                overflow:hidden;
                word-break:normal;
                border-top-width:1px;
                border-bottom-width:1px;
                border-color:#aaa;
                color:#fff;
                background-color:#f38630;
        """,
         'logger_data_cell': """
                font-family:Arial, sans-serif;
                font-size:14px;
                padding:10px 5px;
                border-style:solid;
                border-width:0px;
                overflow:hidden;
                word-break:normal;
                border-color:#aaa;
                color:#333;
                background-color:#fff;
                text-align:center;
         """,
         'logger_name_cell': """
                font-family:Arial, sans-serif;
                font-size:14px;
                padding:10px 5px;
                border-style:solid;
                border-width:0px;
                overflow:hidden;
                word-break:normal;
                border-color:#aaa;
                color:#333;
                background-color:#fff;
         """,
         'queue_data_cell': """
                font-family:Arial, sans-serif;
                font-size:14px;
                padding:10px 5px;
                border-style:solid;
                border-width:0px;
                overflow:hidden;
                word-break:normal;
                border-bottom-width:2px;
                border-color:#aaa;
                color:#333;
                background-color:#FCFBE3;
                text-align:center;
         """,
         'queue_name_cell': """
                font-family:Arial, sans-serif;
                font-size:14px;
                padding:10px 5px;
                border-style:solid;
                border-width:0px;
                overflow:hidden;
                word-break:normal;
                border-bottom-width:2px;
                border-color:#aaa;
                color:#333;
                background-color:#FCFBE3;
         """
         }
EMAIL_TEMPLATE = """
<HTML>

<body>
{% block body %}
  <table style="{{ style.table }}">
  <tr>
    <th style="{{ style.header_cell }}">&nbsp;</th>
    <th style="{{ style.header_cell }}">Retrieved<br>yesterday</th>
    <th style="{{ style.header_cell }}">Weekly<br>coverage</th>
    <th style="{{ style.header_cell }}">Monthly<br>coverage</th>
  </tr>
  {% for queue in queues %}
    {% for datalogger in queue['dataloggers'] %}
      <tr>
        <td style="{{ style.logger_name_cell }}">
          {{ datalogger.name }}
        </td>
        <td style="{{ style.logger_data_cell }}">
          {{ datalogger.daily_total }}
        </td>
        <td style="{{ style.logger_data_cell }}">
          {{ '%d' % datalogger.coverage.weekly }}%
        </td>
        <td style="{{ style.logger_data_cell }}">
          {{ '%d' % datalogger.coverage.monthly }}%
        </td>
      </tr>
    {% endfor %}
    <tr>
      <td style="{{ style.queue_name_cell }}">
        {{ queue.name }}
      </td>
      <td style="{{ style.queue_data_cell }}">
        {{ queue.daily_total }}
      </td>
      <td style="{{ style.queue_data_cell }}">
        {{ '%d' % queue.weekly_coverage }}%
      </td>
      <td style="{{ style.queue_data_cell }}">
        {{ '%d' % queue.monthly_coverage }}%
      </td>
    </tr>
  {% endfor %}
  </table>
{% endblock %}
</body>
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
        return {'weekly': 0, 'monthly': 0}

    coverage = {}
    day = datetime.utcnow().date() - timedelta(1)
    week_ago = day - timedelta(7)
    month_ago = day - timedelta(30)
    weekly_total = 0
    monthly_total = 0
    while day > month_ago:
        out_str = Template(config['out_path']).substitute(config)
        out_path = day.strftime(out_str)
        file = os.path.join(config['out_dir'], out_path)
        if os.path.exists(file):
            monthly_total += 1
            if day > week_ago:
                weekly_total += 1
        day -= timedelta(1)

    coverage['weekly'] = 100 * weekly_total / 7
    coverage['monthly'] = 100 * monthly_total / 30
    logger.debug("%s: weekly: %d / 7 = %f; monthly: %d / 30 = %f",
                 config['name'], weekly_total, coverage['weekly'],
                 monthly_total, coverage['monthly'])
    return coverage


def process_datalogger(config):
    logger_results = {}
    logger_results['name'] = config['name']
    logger_results['disabled'] = 'disabled' in config and config['disabled']

    logger_results['daily_total'] = get_daily_total(config)
    logger_results['coverage'] = get_coverage(config)
    logging_str = "%s daily: %d; weekly: %f; monthly: %f"
    logger.debug(logging_str, config['name'], logger_results['daily_total'],
                 logger_results['coverage']['weekly'],
                 logger_results['coverage']['monthly'])

    return logger_results


def process_queue(config):
    queue = {'name': config['name'], 'dataloggers': []}
    for datalogger in config['dataloggers']:
        logger_results = process_datalogger(datalogger)
        if logger_results is not None:
            queue['dataloggers'].append(logger_results)

    daily_total = 0
    weekly = 0
    monthly = 0
    for datalogger in queue['dataloggers']:
        daily_total += datalogger['daily_total']
        weekly += datalogger['coverage']['weekly']
        monthly += datalogger['coverage']['monthly']

    queue['daily_total'] = daily_total
    queue['weekly_coverage'] = weekly / len(queue['dataloggers'])
    queue['monthly_coverage'] = monthly / len(queue['dataloggers'])
    return queue


def process_queues(config):
    queues = []
    for queue in config['queues']:
        if 'disabled' in queue and queue['disabled']:
            logger.info("Queue %s is disabled, skiping it.", queue['name'])
        else:
            queues.append(process_queue(queue))

    return queues


def send_email(html):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "GPS retreival"
    msg['From'] = tutil.get_env_var('LOG_SENDER')
    msg['To'] = tutil.get_env_var('REPORT_RECIPIENT')

    msg.attach(MIMEText(html, 'html'))

    try:
        s = smtplib.SMTP(tutil.get_env_var('MAILHOST'))
        s.sendmail(tutil.get_env_var('LOG_SENDER'),
                   tutil.get_env_var('REPORT_RECIPIENT'), msg.as_string())

    except OSError as e:
        logger.exception(e)


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
    email = tmpl.render(queues=queues, style=STYLE)
    logger.debug(email)
    send_email(email)
    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

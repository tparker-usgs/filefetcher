#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Retrieve camera images from email attachments."""

from datetime import timedelta, datetime
import logging
import os
import sys
import socket
import struct
import pathlib
from urllib.parse import urlparse
import errno
from multiprocessing import Process
from buffering_smtp_handler import BufferingSMTPHandler
import sys
from imaplib import IMAP4, IMAP4_SSL
import getpass
import email
import datetime

env = None


def exit_with_error(error):
    logger.error(error)
    logging.shutdown()
    sys.exit(1)


def get_env_var(var, required=False, default=None):
    if var in os.environ:
        logger.debug("%s: %s", var, os.environ[var])
        return os.environ[var]

    else:
        if required:
            msg = "Envionment variable {} not set, exiting.".format(var)
            exit_with_error(EnvironmentError(msg))
        else:
            return default


def setup_logging():
    global logger
    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    logger.addHandler(ch)

    try:
        subject = "camfetcher logs"
        handler = BufferingSMTPHandler(os.environ['MAILHOST'],
                                       os.environ['FF_SENDER'],
                                       os.environ['FF_RECIPIENT'], subject,
                                       1000, "%(levelname)s - %(message)s")
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
    except KeyError:
        logger.info("SMTP logging not configured.")


def process_email(msg):
    for attchment in msg.iter_attachments():
        filename=attchment.get_filename()
        if filename is None:
            continue

        sv_path = os.path.join("/tmp/cam", filename)
        if not os.path.isfile(sv_path):
            logger.debug("creating %s", sv_path)
            fp = open(sv_path, 'wb')
            fp.write(attchment.get_payload(decode=True))
            fp.close()


def process_mailbox(M):
    rv, msgs = M.search(None, "UNSEEN")
    msg_nums = msgs[0].split()

    if rv != 'OK':
        logger.debug("No messages found!")
        return

    for num in msg_nums:
        rv, data = M.fetch(num, '(RFC822)')

        if rv != 'OK':
            logger.error("Cannot retrieve message %s", num)
            return

        email_body = data[0][1]
        msg = email.message_from_string(email_body)
        process_email(msg)


def main():
    """Where it all begins."""

    setup_logging()

    with  IMAP4_SSL(get_env_var('IMAPSERVER', required=True)) as M:
        try:
            M.login(get_env_var('CF_USER', required=True),
                    get_env_var('CF_PASSWD', required=True))
        except IMAP4.error:
            exit_with_error("Login failed.")

        for cam in get_env_var('CF_CAMS', required=True).split(':'):
            rv, data = M.select(cam)
            if rv == 'OK':
                logger.debug("Processing mailbox %s", cam)
                process_mailbox(M)
                M.close()

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()

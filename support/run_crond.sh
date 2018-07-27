#!/bin/bash

# prepend application environment variables to crontab
env | grep -v PATH | cat - /app/filefetcher/cron-filefetcher > /etc/cron.d/cron-filefetcher

/usr/sbin/cron -f 

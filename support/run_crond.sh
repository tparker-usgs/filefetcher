#!/bin/bash

# prepend application environment variables to crontab
env | grep -v PATH | cat - /app/filefetcher/cron-camfetcher > /etc/cron.d/cron-camfetcher

/usr/sbin/cron -f 

#!/bin/bash

# prepend application environment variables to crontab
env | grep -v PATH | cat - /app/gpspull/cron-gpspull > /etc/cron.d/cron-gpspull

/usr/sbin/cron -f 

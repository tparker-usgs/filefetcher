#!/bin/sh

# cron is fussy about this
chmod 644 cron-gpsPull

#systemctl stop mirrorGina.service && \

docker build -t gpspull .
docker stop gpspull 
docker rm gpspull 
docker run --detach=true --env-file=/home/tparker/private/gpspull.env --name gpspull gpspull


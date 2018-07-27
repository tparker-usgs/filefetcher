#!/bin/sh

support/build.sh
if [ $? == 0 ]; then
    docker stop camfetcher
    docker rm camfetcher
    docker run \
        --restart=always \
        --detach=true \
        --mount type=bind,src=$HOME/camfetcher,dst=/data \
        --env-file=$HOME/private/camfetcher.env \
        --name camfetcher \
        camfetcher
else
    echo "Build failed, exiting."
fi

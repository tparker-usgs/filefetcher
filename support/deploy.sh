#!/bin/sh

support/build.sh
if [ $? == 0 ]; then
    docker stop filefetcher
    docker rm filefetcher
    docker run \
        --restart=always \
        --detach=true \
        --mount type=bind,src=$HOME/filefetcher,dst=/data \
        --env-file=$HOME/private/filefetcher.env \
        --name filefetcher \
        filefetcher
else
    echo "Build failed, exiting."
fi

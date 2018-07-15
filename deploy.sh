#!/bin/sh

./build.sh
if [ $? == 0 ]; then
    docker stop gpspull
    docker rm gpspull
    docker run \
        --restart=always \
        --detach=true \
        --mount type=bind,src=/Users/tomp/gpspull,dst=/data \
        --env-file=/Users/tomp/private/gpspull.env \
        --name gpspull \
        gpspull
else
    echo "Build failed, exiting."
fi

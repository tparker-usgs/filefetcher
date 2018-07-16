docker build -t gpspull .

VERSION=`cat VERSION`
docker tag  gpspull:latest gpspull:$VERSION

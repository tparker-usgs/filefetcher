docker build -t filefetcher .

VERSION=`cat VERSION`
docker tag filefetcher:latest filefetcher:$VERSION

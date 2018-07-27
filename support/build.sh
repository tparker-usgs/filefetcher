docker build -t camfetcher .

VERSION=`cat VERSION`
docker tag camfetcher:latest camfetcher:$VERSION

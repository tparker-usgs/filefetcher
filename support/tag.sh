#!/bin/sh

VERSION=`python -c "import filefetcher; print(filefetcher.__version__)"`
echo $VERSION
git add filefetcher/version.py
git commit -m 'version bump'
git push \
&& git tag $VERSION \
&& git push --tags


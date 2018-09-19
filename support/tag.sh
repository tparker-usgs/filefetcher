#!/bin/sh

git add VERSION
git commit -m 'version bump'
git push \
&& git tag `cat VERSION` \
&& git push --tags

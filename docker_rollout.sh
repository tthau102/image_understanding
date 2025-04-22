#!/bin/bash

if [ -n "$1" ]; then
    ver="$1"
else
    echo "Please provide a version number in \$1"
    exit
fi

docker build -t image-understanding-app-tokyo:$ver .
docker tag image-understanding-app-tokyo:$ver image-understanding-app-tokyo:latest

docker stop image-understanding-app-tokyo
docker rm image-understanding-app-tokyo
docker run -dt -p 80:8080 -v ~/.aws:/root/.aws --name image-understanding-app-tokyo image-understanding-app-tokyo
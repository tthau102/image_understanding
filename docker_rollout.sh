#!/bin/bash

IMAGE_NAME="image-understanding-app-tokyo"

if [ -n "$1" ]; then
    IMAGE_TAG="$1"
    if docker images "$IMAGE_NAME:$IMAGE_TAG" | grep -q "$IMAGE_TAG"; then
        echo "Image $IMAGE_NAME:$IMAGE_TAG exists locally."
        exit
    fi
else
    echo "Please provide a version number in \$1"
    exit
fi

docker build -t $IMAGE_NAME:$IMAGE_TAG .
docker tag $IMAGE_NAME:$IMAGE_TAG $IMAGE_NAME:latest

docker stop $IMAGE_NAME
docker rm $IMAGE_NAME

# Sử dụng environment variables cho AWS credentials

docker run -dt -p 80:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_SESSION_TOKEN=$(aws configure get aws_session_token) \
  -e AWS_REGION=$(aws configure get region) \
  --name $IMAGE_NAME $IMAGE_NAME
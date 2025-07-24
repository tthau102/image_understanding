#!/bin/bash

IMAGE_NAME="tthau-ui"

VERSION=$(date +"%d.%m.%y.%H.%M.%S")

IMAGE_TAG=$VERSION

# Build và tag image
docker build -t $IMAGE_NAME:$IMAGE_TAG .
docker tag $IMAGE_NAME:$IMAGE_TAG $IMAGE_NAME:latest

# Stop và remove container cũ
docker stop $IMAGE_NAME
docker rm $IMAGE_NAME

# Sử dụng environment variables cho AWS credentials
docker run -dt -p 8068:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_SESSION_TOKEN=$(aws configure get aws_session_token) \
  -e AWS_REGION=$(aws configure get region) \
  --name $IMAGE_NAME $IMAGE_NAME

sleep 1
docker logs $IMAGE_NAME
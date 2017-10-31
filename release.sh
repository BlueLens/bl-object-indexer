#!/usr/bin/env bash

export ORG="bluelens"
export IMAGE="bl-image-indexer"
export TAG='latest'
export NAMESPACE="index"

docker login

docker build -t $IMAGE:$TAG .
docker tag $IMAGE:$TAG $ORG/$IMAGE:$TAG
docker push $ORG/$IMAGE:$TAG



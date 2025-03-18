#!/bin/bash

set -e

# Usage example: ./truvity-build-tag-push.sh 0.0.4

readonly version=${1:?}

cd "$(dirname "$0")"

readonly image_full="562116914481.dkr.ecr.eu-west-1.amazonaws.com/k8s/aws-alb-oauth-proxy:$version"

docker build . -t "$image_full"
AWS_PROFILE=infra@power docker push "$image_full"

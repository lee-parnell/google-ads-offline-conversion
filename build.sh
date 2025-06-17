
#!/usr/bin/env bash
set -euo pipefail

# config
PY_VERSION="3.12"           
ARCH="x86_64"               
IMAGE="public.ecr.aws/lambda/python:${PY_VERSION}-${ARCH}"

BUILD_DIR="package"
ZIP_NAME="package.zip"

# pre-cleanup and creating package dir
rm -rf "$BUILD_DIR" "$ZIP_NAME"
mkdir -p "$BUILD_DIR"

# install dependencies using lambda runtime
echo "Pulling $IMAGE and python deps …"
docker run --rm \
  --platform "linux/${ARCH}" \
  --entrypoint /bin/bash \
  -v "$PWD":/var/task \
  -w /var/task \
  "$IMAGE" -c "
    set -euo pipefail
    pip install --upgrade --no-cache-dir \
        -r requirements.txt \
        -t ${BUILD_DIR}
  "

# package application as it is specified in aws docs
echo "Packaging the app source code as flat dir structure inside package"
cd package && zip -r ../package.zip . && cd -
zip -r package.zip google-ads-credentials.json
cd app/aws-lambda && zip -r ../../package.zip lambda_function.py && cd -
cd app/ && zip -r ../package.zip . -x aws-lambda/* && cd - # exclude lambda_function to avoid duplication and namespace conflict
rm -rf "$BUILD_DIR"

echo "\n\n${ZIP_NAME} created ($(du -h ${ZIP_NAME} | cut -f1)) — ready for S3/Lambda upload"

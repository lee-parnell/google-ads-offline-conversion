#!/bin/bash

mkdir -p package

echo "Installing Pytohn dependencies"
pip install -r requirements.txt -t ./package

echo "Packaging the app source code as flat dir structure inside package"
cd package && zip -r ../package.zip . && cd -
zip -r package.zip google-ads-credentials.json
cd app/aws-lambda && zip -r ../../package.zip lambda_function.py && cd -
cd app/ && zip -r ../package.zip . -x aws-lambda/* && cd - # exclude lambda_function to avoid duplication and namespace conflict

echo "kommo offline conversion package is ready for deployment"


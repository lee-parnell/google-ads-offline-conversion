# kommo-google-ads-offline-conversion
Simple yet production-ready AWS Lambda stack that syncs **Google Ads identifiers (gclid/gbraid)** captured on your landing pages WhatApp buttons to Kommo CRM leads and automatically uploads **offline conversions** back to Google Ads using enriched lead fields.

# How it works?
1. Track outbound WhatsApp clicks
`logOutboundClick` captures click identifiers from the URL and sends the tracking data to the `/outbound-click-logs` endpoint.
2. AWS Lambda
- Stores clicks logs to DynamoDB with specified TTL
- Matches incoming WhatsApp messages with click logs
- Updates and enriches lead with fields
- Uploades offline conversion to Google Ads based on Kommo pipeline stage
3. Kommo integration
`KommoService` uses Kommo's API to:
- Retrieve leads and associated contacts
- Updates custom fields
4. Google Ads API Integration
- Hashes user identifiers (email/phone)
- Uploads offline conversions using the proper conversion action

# How to use?
## Prerequisites
- Docker
- AWS Lambda & API Gateway & DynamoDB
- Kommo API access
- Google Ads API **Basic Level** access
## Build and Package the app
```sh
chmod +x build.sh
./build.sh # produces ~70mb artifact
```
## Deployment
- Deploy the application via S3 upload as it is specified in AWS docs: https://docs.aws.amazon.com/lambda/latest/dg/python-package.html
- AWS secret manager ENV vars

## Wire endpoints

## Embed tracking script


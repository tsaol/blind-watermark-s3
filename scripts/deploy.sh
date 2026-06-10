#!/bin/bash
set -e

STACK_NAME="${1:-blind-watermark}"
REGION="${2:-ap-northeast-1}"
BUCKET_NAME="${3:-blind-watermark-source-$(aws sts get-caller-identity --query Account --output text)}"

echo "Deploying stack: ${STACK_NAME}"
echo "Region: ${REGION}"
echo "Bucket: ${BUCKET_NAME}"

sam build --use-container

sam deploy \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --resolve-s3 \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides "SourceBucketName=${BUCKET_NAME}" \
    --no-confirm-changeset

echo ""
echo "Deployment complete. Outputs:"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs" \
    --output table

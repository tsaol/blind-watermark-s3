#!/bin/bash
set -e

REGION="${AWS_DEFAULT_REGION:-ap-northeast-1}"
STACK_NAME="${STACK_NAME:-blind-watermark}"
ARTIFACT_BUCKET="${ARTIFACT_BUCKET:-}"

echo "=== Blind Watermark - Automated Deploy ==="
echo "Region: $REGION"
echo "Stack:  $STACK_NAME"
echo ""

# Check prerequisites
command -v aws >/dev/null 2>&1 || { echo "Error: aws cli not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "Error: zip not found"; exit 1; }

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Set default artifact bucket if not provided
if [ -z "$ARTIFACT_BUCKET" ]; then
    ARTIFACT_BUCKET="blind-watermark-artifacts-${ACCOUNT_ID}"
fi
echo "Artifact bucket: $ARTIFACT_BUCKET"
echo ""

# Step 1: Create artifact bucket
echo "[1/6] Creating artifact bucket..."
if aws s3 ls "s3://$ARTIFACT_BUCKET" --region "$REGION" 2>/dev/null; then
    echo "  Bucket already exists, skipping."
else
    aws s3 mb "s3://$ARTIFACT_BUCKET" --region "$REGION"
    echo "  Created."
fi

# Step 2: Build Lambda layer
echo "[2/6] Building Lambda layer..."
rm -rf build/layer
mkdir -p build/layer/python
pip install numpy opencv-python-headless Pillow \
    -t build/layer/python \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --quiet
(cd build/layer && zip -r9q ../../layer.zip python/)
echo "  Layer built: $(du -h layer.zip | cut -f1)"

# Step 3: Package Lambda functions
echo "[3/6] Packaging Lambda functions..."
rm -f embed.zip extract.zip

cp src/shared/watermark.py src/embed/watermark.py
cp src/shared/watermark.py src/extract/watermark.py

(cd src/embed && zip -r9q ../../embed.zip .)
(cd src/extract && zip -r9q ../../extract.zip .)

rm -f src/embed/watermark.py src/extract/watermark.py

echo "  embed.zip:   $(du -h embed.zip | cut -f1)"
echo "  extract.zip: $(du -h extract.zip | cut -f1)"

# Step 4: Upload to S3
echo "[4/6] Uploading artifacts to S3..."
aws s3 cp layer.zip "s3://$ARTIFACT_BUCKET/deploy/layer.zip" --region "$REGION" --quiet
aws s3 cp embed.zip "s3://$ARTIFACT_BUCKET/deploy/embed.zip" --region "$REGION" --quiet
aws s3 cp extract.zip "s3://$ARTIFACT_BUCKET/deploy/extract.zip" --region "$REGION" --quiet
echo "  Done."

# Step 5: Deploy CloudFormation
echo "[5/6] Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --parameter-overrides \
        ArtifactBucket="$ARTIFACT_BUCKET" \
        ArtifactPrefix=deploy \
    --no-fail-on-empty-changeset

echo "  Stack deployed."

# Step 6: Verify
echo "[6/6] Verifying..."
EMBED_FN=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query 'StackResources[?LogicalResourceId==`EmbedFunction`].PhysicalResourceId' \
    --output text)
EXTRACT_FN=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query 'StackResources[?LogicalResourceId==`ExtractFunction`].PhysicalResourceId' \
    --output text)

echo "  Embed function:  $EMBED_FN"
echo "  Extract function: $EXTRACT_FN"
echo ""
echo "=== Deploy complete! ==="
echo ""
echo "Test with:"
echo "  aws lambda invoke --function-name $EMBED_FN --region $REGION \\"
echo "    --payload '{\"body\":\"{\\\"key\\\":\\\"tmp/test.jpg\\\",\\\"user_id\\\":\\\"alice\\\"}\"}' out.json"

# Cleanup build artifacts
rm -rf build layer.zip embed.zip extract.zip

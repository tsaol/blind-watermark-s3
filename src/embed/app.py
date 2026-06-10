import json
import base64
import os

import boto3

from watermark import embed

s3_client = boto3.client("s3")
SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET", "blind-watermark-source-342367142984")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        key = body.get("key")
        user_id = body.get("user_id", "anonymous")

        if not key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'key' parameter"}),
            }

        response = s3_client.get_object(Bucket=SOURCE_BUCKET, Key=key)
        original_image = response["Body"].read()

        watermarked_image = embed(original_image, user_id)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "image/png"},
            "isBase64Encoded": True,
            "body": base64.b64encode(watermarked_image).decode(),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

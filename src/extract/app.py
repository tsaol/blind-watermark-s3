import json
import base64

from watermark import extract


def lambda_handler(event, context):
    try:
        body = event.get("body", "")
        if event.get("isBase64Encoded", False):
            image_bytes = base64.b64decode(body)
        else:
            payload = json.loads(body)
            image_bytes = base64.b64decode(payload["image"])

        user_id = extract(image_bytes)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"user_id": user_id, "status": "extracted"}),
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e), "status": "failed"}),
        }

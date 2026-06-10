import json
import urllib.request

import boto3

from watermark import embed

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    object_context = event["getObjectContext"]
    request_route = object_context["outputRoute"]
    request_token = object_context["outputToken"]
    input_s3_url = object_context["inputS3Url"]

    user_headers = event.get("userRequest", {}).get("headers", {})
    user_id = user_headers.get("x-watermark-user-id", "anonymous")

    try:
        response = urllib.request.urlopen(input_s3_url)
        original_image = response.read()

        watermarked_image = embed(original_image, user_id)

        s3_client.write_get_object_response(
            Body=watermarked_image,
            RequestRoute=request_route,
            RequestToken=request_token,
            ContentType="image/png",
            Metadata={"x-watermark-embedded": "true"},
        )

        return {"statusCode": 200}

    except Exception as e:
        s3_client.write_get_object_response(
            Body=json.dumps({"error": str(e)}).encode(),
            RequestRoute=request_route,
            RequestToken=request_token,
            StatusCode=500,
            ContentType="application/json",
        )
        return {"statusCode": 500}

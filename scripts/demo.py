#!/usr/bin/env python3
"""Demo: upload image, retrieve with watermark, extract user ID."""

import argparse
import base64
import json
import sys
import os

import boto3
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "shared"))
from watermark import embed, extract, compute_psnr


def demo_local(image_path: str, user_id: str):
    """Run embed/extract locally without AWS."""
    with open(image_path, "rb") as f:
        original = f.read()

    print(f"Original size: {len(original)} bytes")
    print(f"Embedding user_id: '{user_id}'")

    watermarked = embed(original, user_id)
    print(f"Watermarked size: {len(watermarked)} bytes")

    psnr = compute_psnr(original, watermarked)
    print(f"PSNR: {psnr:.2f}dB (>35dB = visually identical)")

    extracted = extract(watermarked)
    print(f"Extracted user_id: '{extracted}'")
    print(f"Match: {extracted == user_id}")

    out_path = image_path.rsplit(".", 1)[0] + "_watermarked.png"
    with open(out_path, "wb") as f:
        f.write(watermarked)
    print(f"Saved watermarked image: {out_path}")


def demo_aws(image_path: str, user_id: str, stack_name: str, region: str):
    """Run full AWS flow: upload -> retrieve via Object Lambda -> extract via API."""
    cf = boto3.client("cloudformation", region_name=region)
    outputs = cf.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    output_map = {o["OutputKey"]: o["OutputValue"] for o in outputs}

    olap_arn = output_map["ObjectLambdaAccessPointArn"]
    extract_url = output_map["ExtractApiUrl"]
    bucket_name = output_map["ImageBucketName"]

    s3 = boto3.client("s3", region_name=region)
    key = f"demo/{os.path.basename(image_path)}"

    print(f"Uploading {image_path} to s3://{bucket_name}/{key}")
    s3.upload_file(image_path, bucket_name, key)

    print(f"Retrieving via Object Lambda (user_id={user_id})...")
    s3_olap = boto3.client("s3", region_name=region)
    response = s3_olap.get_object(
        Bucket=olap_arn,
        Key=key,
        RequestHeaders={"x-watermark-user-id": user_id},
    )
    watermarked = response["Body"].read()
    print(f"Received watermarked image: {len(watermarked)} bytes")

    print(f"Extracting via API: {extract_url}")
    resp = requests.post(
        extract_url,
        json={"image": base64.b64encode(watermarked).decode()},
    )
    result = resp.json()
    print(f"Extract result: {json.dumps(result, indent=2)}")
    print(f"Match: {result.get('user_id') == user_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blind watermark demo")
    parser.add_argument("image", help="Path to test image")
    parser.add_argument("--user-id", default="demo-user-001", help="User ID to embed")
    parser.add_argument("--aws", action="store_true", help="Run against deployed AWS stack")
    parser.add_argument("--stack-name", default="blind-watermark")
    parser.add_argument("--region", default="ap-northeast-1")

    args = parser.parse_args()

    if args.aws:
        demo_aws(args.image, args.user_id, args.stack_name, args.region)
    else:
        demo_local(args.image, args.user_id)

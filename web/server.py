import json
import base64
import os

import boto3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app, origins=["https://liucao.me", "http://localhost:*"])

lambda_client = boto3.client("lambda", region_name="ap-northeast-1")
s3_client = boto3.client("s3", region_name="ap-northeast-1")

SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET", "blind-watermark-source-342367142984")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/embed", methods=["POST"])
def embed():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    user_id = request.form.get("user_id", "anonymous")
    image_bytes = file.read()

    # Upload to S3 temporarily
    key = f"tmp/{file.filename}"
    s3_client.put_object(Bucket=SOURCE_BUCKET, Key=key, Body=image_bytes)

    # Call embed Lambda
    payload = {"body": json.dumps({"key": key, "user_id": user_id})}
    response = lambda_client.invoke(
        FunctionName="blind-watermark-embed",
        Payload=json.dumps(payload).encode(),
    )
    result = json.loads(response["Payload"].read())

    if result.get("statusCode") != 200:
        body = json.loads(result.get("body", "{}"))
        return jsonify({"error": body.get("error", "Unknown error")}), 500

    return jsonify({
        "image": result["body"],
        "user_id": user_id,
        "original_size": len(image_bytes),
    })


@app.route("/api/extract", methods=["POST"])
def extract():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    image_bytes = file.read()
    img_b64 = base64.b64encode(image_bytes).decode()

    payload = {"body": json.dumps({"image": img_b64})}
    response = lambda_client.invoke(
        FunctionName="blind-watermark-extract",
        Payload=json.dumps(payload).encode(),
    )
    result = json.loads(response["Payload"].read())
    body = json.loads(result.get("body", "{}"))

    return jsonify(body)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

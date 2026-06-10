# Blind Watermark S3 Object Lambda

Invisible (blind) watermarking solution using AWS S3 Object Lambda. Embeds a per-user ID into images at retrieval time using DCT frequency domain techniques. The watermark is invisible to the human eye but can be extracted later to trace image leaks.

## Architecture

```
Client GET (x-watermark-user-id header)
    → S3 Object Lambda Access Point
    → Lambda embeds invisible watermark
    → Returns visually-identical image with hidden user ID

Verify endpoint:
    POST /extract (image) → returns embedded user_id
```

## How It Works

- **Algorithm**: DCT-based frequency domain watermarking
- **Embedding**: Modifies mid-frequency DCT coefficients in the Y (luminance) channel
- **Detection**: Blind extraction (no original image needed)
- **Robustness**: Survives JPEG compression (quality 85+), PNG re-encoding
- **Quality**: PSNR > 38dB (visually indistinguishable from original)

## Quick Start (Local)

```bash
# Test locally without AWS
python scripts/demo.py test_image.png --user-id "user-123"
```

## Deploy to AWS

```bash
# Build Lambda layer
chmod +x layer/build.sh && ./layer/build.sh

# Deploy with SAM
chmod +x scripts/deploy.sh
./scripts/deploy.sh blind-watermark ap-northeast-1
```

## Usage

### Embed (automatic on retrieval)

```bash
# Retrieve image through Object Lambda Access Point
aws s3api get-object \
    --bucket <OLAP-ARN> \
    --key photos/secret.png \
    --request-headers '{"x-watermark-user-id": "user-456"}' \
    output.png
```

### Extract (verify a suspect image)

```bash
curl -X POST https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/Prod/extract \
    -H "Content-Type: application/json" \
    -d "{\"image\": \"$(base64 -w0 suspect_image.png)\"}"
```

Response:
```json
{"user_id": "user-456", "status": "extracted"}
```

## Project Structure

```
├── template.yaml          # SAM template
├── src/
│   ├── shared/watermark.py   # Core DCT watermark algorithm
│   ├── embed/app.py          # S3 Object Lambda handler
│   └── extract/app.py        # API Gateway handler
├── layer/                 # Lambda layer (numpy, opencv, Pillow)
├── tests/                 # Unit + robustness tests
└── scripts/               # Deploy and demo scripts
```

## Tests

```bash
python tests/test_watermark.py
```

## Limitations

- Max user ID length: depends on image size (64 chars for 512x512+)
- Minimum image size: 256x256 pixels
- Heavy edits (crop >50%, aggressive resize) may destroy the watermark
- JPEG quality below 75 may corrupt extraction

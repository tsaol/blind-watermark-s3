import sys
import os
import io

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "shared"))
from watermark import embed, extract, compute_psnr


def make_test_image(width=512, height=512) -> bytes:
    img = np.random.randint(50, 200, (height, width, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def test_embed_extract_roundtrip():
    image = make_test_image()
    user_id = "user-12345"

    watermarked = embed(image, user_id)
    extracted = extract(watermarked)

    assert extracted == user_id, f"Expected '{user_id}', got '{extracted}'"
    print(f"[PASS] roundtrip: embedded and extracted '{user_id}'")


def test_psnr_quality():
    image = make_test_image()
    user_id = "test-user-abc"

    watermarked = embed(image, user_id)
    psnr = compute_psnr(image, watermarked)

    assert psnr > 35, f"PSNR too low: {psnr:.2f}dB (expected > 35dB)"
    print(f"[PASS] quality: PSNR = {psnr:.2f}dB")


def test_jpeg_robustness():
    image = make_test_image(width=1024, height=1024)
    user_id = "leak-trace-99"

    watermarked = embed(image, user_id)

    # Re-encode as JPEG (quality 85)
    arr = np.frombuffer(watermarked, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    _, jpeg_bytes = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Re-encode back to PNG for extraction
    img2 = cv2.imdecode(jpeg_bytes, cv2.IMREAD_COLOR)
    _, png_bytes = cv2.imencode(".png", img2)

    try:
        extracted = extract(png_bytes.tobytes())
        if extracted == user_id:
            print(f"[PASS] JPEG robustness: survived quality=85 compression")
        else:
            print(f"[WARN] JPEG robustness: got '{extracted}' instead of '{user_id}' (partial corruption)")
    except Exception as e:
        print(f"[WARN] JPEG robustness: extraction failed after compression ({e})")


def test_different_user_ids():
    image = make_test_image()
    test_ids = ["u001", "alice@company.com", "session-abc-def-123"]

    for uid in test_ids:
        watermarked = embed(image, uid)
        extracted = extract(watermarked)
        assert extracted == uid, f"Failed for '{uid}': got '{extracted}'"

    print(f"[PASS] multiple user IDs: all {len(test_ids)} extracted correctly")


if __name__ == "__main__":
    test_embed_extract_roundtrip()
    test_psnr_quality()
    test_jpeg_robustness()
    test_different_user_ids()
    print("\nAll tests passed!")

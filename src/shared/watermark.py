import numpy as np
import cv2


BLOCK_SIZE = 8
COEFF_POS = (4, 3)
STRENGTH = 50.0
REDUNDANCY = 5


def _text_to_bits(text: str) -> list[int]:
    data = text.encode("utf-8")
    length_bits = format(len(data), "016b")
    payload_bits = "".join(format(b, "08b") for b in data)
    return [int(b) for b in length_bits + payload_bits]


def _bits_to_text(bits: list[int]) -> str:
    length_str = "".join(str(b) for b in bits[:16])
    length = int(length_str, 2)
    payload = bits[16 : 16 + length * 8]
    chars = []
    for i in range(0, len(payload), 8):
        byte = int("".join(str(b) for b in payload[i : i + 8]), 2)
        chars.append(byte)
    return bytes(chars).decode("utf-8")


def _get_blocks(y_channel: np.ndarray):
    h, w = y_channel.shape
    bh = h // BLOCK_SIZE
    bw = w // BLOCK_SIZE
    blocks = []
    for r in range(bh):
        for c in range(bw):
            row = r * BLOCK_SIZE
            col = c * BLOCK_SIZE
            blocks.append((row, col))
    return blocks


def embed(image_bytes: bytes, user_id: str) -> bytes:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")

    img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y_channel = img_ycrcb[:, :, 0].astype(np.float64)

    blocks = _get_blocks(y_channel)
    bits = _text_to_bits(user_id)
    blocks_needed = len(bits) * REDUNDANCY

    if blocks_needed > len(blocks):
        max_chars = len(blocks) // REDUNDANCY // 8 - 2
        raise ValueError(
            f"Image too small: need {blocks_needed} blocks, have {len(blocks)}. "
            f"Max payload: {max_chars} chars"
        )

    for bit_idx, bit in enumerate(bits):
        for rep in range(REDUNDANCY):
            block_idx = bit_idx * REDUNDANCY + rep
            row, col = blocks[block_idx]

            block = y_channel[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
            dct_block = cv2.dct(block)

            # Quantization-based embedding: force coefficient to known magnitude
            if bit == 1:
                dct_block[COEFF_POS] = STRENGTH
            else:
                dct_block[COEFF_POS] = -STRENGTH

            y_channel[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE] = cv2.idct(
                dct_block
            )

    y_channel = np.clip(y_channel, 0, 255)
    img_ycrcb[:, :, 0] = y_channel.astype(np.uint8)
    result = cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR)

    _, encoded = cv2.imencode(".png", result)
    return encoded.tobytes()


def extract(image_bytes: bytes) -> str:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")

    img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y_channel = img_ycrcb[:, :, 0].astype(np.float64)

    blocks = _get_blocks(y_channel)

    # First extract length (16 bits)
    length_bits = []
    for bit_idx in range(16):
        votes = 0.0
        for rep in range(REDUNDANCY):
            block_idx = bit_idx * REDUNDANCY + rep
            if block_idx >= len(blocks):
                break
            row, col = blocks[block_idx]
            block = y_channel[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
            dct_block = cv2.dct(block)
            votes += dct_block[COEFF_POS]
        length_bits.append(1 if votes > 0 else 0)

    payload_length = int("".join(str(b) for b in length_bits), 2)
    if payload_length <= 0 or payload_length > 64:
        raise ValueError(f"Invalid payload length: {payload_length}")

    total_bits = 16 + payload_length * 8
    all_bits = []
    for bit_idx in range(total_bits):
        votes = 0.0
        for rep in range(REDUNDANCY):
            block_idx = bit_idx * REDUNDANCY + rep
            if block_idx >= len(blocks):
                break
            row, col = blocks[block_idx]
            block = y_channel[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
            dct_block = cv2.dct(block)
            votes += dct_block[COEFF_POS]
        all_bits.append(1 if votes > 0 else 0)

    return _bits_to_text(all_bits)


def compute_psnr(original_bytes: bytes, watermarked_bytes: bytes) -> float:
    arr1 = np.frombuffer(original_bytes, dtype=np.uint8)
    arr2 = np.frombuffer(watermarked_bytes, dtype=np.uint8)
    img1 = cv2.imdecode(arr1, cv2.IMREAD_COLOR)
    img2 = cv2.imdecode(arr2, cv2.IMREAD_COLOR)

    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    return cv2.PSNR(img1, img2)

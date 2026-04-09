# tools/common/image_utils.py
"""图片处理工具模块 - 哈希计算与图片处理"""

import hashlib
import logging

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def compute_dhash(image_data: bytes) -> str:
    """
    计算图片的差值哈希 (dHash)

    Args:
        image_data: 图片的二进制数据

    Returns:
        64位十六进制哈希字符串
    """
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(image_data)).convert("L").resize((9, 8))
        pixels = list(img.getdata())

        diff = []
        for row in range(8):
            for col in range(8):
                left_pixel = pixels[row * 9 + col]
                right_pixel = pixels[row * 9 + col + 1]
                diff.append(left_pixel > right_pixel)

        decimal_value = 0
        hash_string = ""
        for i, value in enumerate(diff):
            if value:
                decimal_value += 2 ** (i % 8)
            if (i % 8) == 7:
                hash_string += hex(decimal_value)[2:].rjust(2, "0")
                decimal_value = 0

        return hash_string
    except ImportError:
        logger.warning("[image_utils] PIL not available, falling back to MD5")
        return compute_md5_hash(image_data)
    except Exception as e:
        logger.error(f"[image_utils] dHash computation failed: {e}")
        return compute_md5_hash(image_data)


def compute_md5_hash(image_data: bytes) -> str:
    """
    计算图片的 MD5 哈希（用于精确匹配）

    Args:
        image_data: 图片的二进制数据

    Returns:
        32位十六进制MD5哈希字符串
    """
    return hashlib.md5(image_data).hexdigest()


def compute_phash(image_data: bytes, hash_size: int = 8) -> str:
    """
    计算图片的感知哈希 (pHash)

    Args:
        image_data: 图片的二进制数据
        hash_size: 哈希大小，默认8

    Returns:
        十六进制哈希字符串
    """
    try:
        import io

        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_data)).convert("L").resize((hash_size + 1, hash_size))
        pixels = np.array(img, dtype=np.float32)

        dct = np.fft.dct(pixels)
        dct_low = dct[:hash_size, :hash_size]

        median_val = np.median(dct_low)
        diff = dct_low > median_val

        hash_int = 0
        for i in range(hash_size):
            for j in range(hash_size):
                if diff[i, j]:
                    hash_int |= 1 << (i * hash_size + j)

        return hex(hash_int)[2:].rjust(hash_size * hash_size // 4, "0")
    except ImportError:
        logger.warning("[image_utils] numpy not available, falling back to dHash")
        return compute_dhash(image_data)
    except Exception as e:
        logger.error(f"[image_utils] pHash computation failed: {e}")
        return compute_dhash(image_data)


def get_image_hash(image_data: bytes, hash_type: str = "dhash") -> str:
    """
    获取图片哈希

    Args:
        image_data: 图片的二进制数据
        hash_type: 哈希类型 ("dhash", "md5", "phash")

    Returns:
        哈希字符串
    """
    if hash_type == "md5":
        return compute_md5_hash(image_data)
    elif hash_type == "phash":
        return compute_phash(image_data)
    else:
        return compute_dhash(image_data)


class ImageHasher:
    """图片哈希计算器类"""

    def __init__(self, hash_type: str = "dhash"):
        self.hash_type = hash_type

    def compute(self, image_data: bytes) -> str:
        """计算图片哈希"""
        return get_image_hash(image_data, self.hash_type)

    def compute_multiple(self, image_data_list: list) -> list:
        """批量计算图片哈希"""
        return [self.compute(data) for data in image_data_list]

"""vision_utils.py

图像截取、OCR 检索以及模板匹配的通用工具函数。
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageGrab


def capture_screen_bgr() -> np.ndarray:
    """截取当前屏幕并返回 BGR 彩色图像。

    Returns:
        np.ndarray: OpenCV 使用的 BGR 三通道数组。
    """

    image = ImageGrab.grab()
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def find_text_boxes(
    image_bgr: np.ndarray,
    keywords: Union[str, Sequence[str]],
    conf_min: int = 60,
    lang: str = "chi_sim+eng",
) -> List[Tuple[int, int, int, int, str]]:
    """在图像中查找包含指定关键词的文本区域。

    Args:
        image_bgr (np.ndarray): 待搜索的 BGR 图像数据。
        keywords (Union[str, Sequence[str]]): 目标文字或关键词列表，匹配时忽略大小写。
        conf_min (int, optional): OCR 结果的最低置信度阈值。默认值为 60。
        lang (str, optional): Tesseract OCR 使用的语言配置。默认值为 "chi_sim+eng"。

    Returns:
        List[Tuple[int, int, int, int, str]]: 匹配到的文本区域列表，每个元素为 (x, y, w, h, text)。
    """

    rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    ocr_data = pytesseract.image_to_data(
        pil_image,
        output_type=pytesseract.Output.DICT,
        lang=lang,
        config="--psm 6",
    )

    matched_boxes: List[Tuple[int, int, int, int, str]] = []
    keyword_list: Iterable[str]
    if isinstance(keywords, (list, tuple, set)):
        keyword_list = keywords
    else:
        keyword_list = [keywords]

    for index, text in enumerate(ocr_data["text"]):
        if not text:
            continue
        if int(ocr_data["conf"][index]) < conf_min:
            continue

        for keyword in keyword_list:
            if keyword.lower() in text.lower():
                left = int(ocr_data["left"][index])
                top = int(ocr_data["top"][index])
                width = int(ocr_data["width"][index])
                height = int(ocr_data["height"][index])
                matched_boxes.append((left, top, width, height, text))
                break

    return matched_boxes


def find_template_matches(
    image_bgr: np.ndarray,
    template_bgr: np.ndarray,
    threshold: float = 0.85,
) -> List[Tuple[int, int, int, int, float]]:
    """在图像中查找与模板相匹配的区域。

    Args:
        image_bgr (np.ndarray): 待搜索的 BGR 图像数据。
        template_bgr (np.ndarray): 模板图像的 BGR 数据，需与目标区域尺寸一致。
        threshold (float, optional): 模板匹配的相似度阈值，范围 0-1。默认值为 0.85。

    Returns:
        List[Tuple[int, int, int, int, float]]: 匹配结果列表，每个元素为 (x, y, w, h, score)。
    """

    if template_bgr is None or template_bgr.size == 0:
        return []

    result = cv2.matchTemplate(image_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    height, width = template_bgr.shape[:2]

    matches: List[Tuple[int, int, int, int, float]] = []
    occupied: List[Tuple[int, int]] = []

    for point in zip(*locations[::-1]):
        x_coord, y_coord = point
        score = float(result[y_coord, x_coord])

        if any(abs(x_coord - ox) < width // 2 and abs(y_coord - oy) < height // 2 for ox, oy in occupied):
            continue

        matches.append((x_coord, y_coord, width, height, score))
        occupied.append((x_coord, y_coord))

    return matches


__all__ = [
    "capture_screen_bgr",
    "find_text_boxes",
    "find_template_matches",
]



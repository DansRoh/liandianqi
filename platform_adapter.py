"""platform_adapter.py

提供跨平台的屏幕捕获与鼠标操作适配层。
"""
from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass
from typing import Protocol, Tuple

import cv2
import numpy as np


class PlatformAdapter(Protocol):
    def capture_screen_bgr(self) -> np.ndarray:
        """截取当前屏幕并返回 BGR 彩色图像。"""

    def random_click_in_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        padding: int = 2,
    ) -> Tuple[float, float]:
        """在矩形范围内随机点击一个点，返回实际点击坐标。"""


@dataclass
class _MacAdapter:
    def __post_init__(self) -> None:
        from mac_mouse import random_click_in_rect as _mac_random_click
        from vision_utils import capture_screen_bgr as _mac_capture

        self._random_click = _mac_random_click
        self._capture = _mac_capture

    def capture_screen_bgr(self) -> np.ndarray:
        return self._capture()

    def random_click_in_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        padding: int = 2,
    ) -> Tuple[float, float]:
        return self._random_click(x, y, width, height, padding=padding)


@dataclass
class _PyAutoGUIAdapter:
    move_steps: Tuple[int, int] = (4, 8)
    step_delay_range: Tuple[float, float] = (0.01, 0.03)

    def __post_init__(self) -> None:
        import pyautogui  # type: ignore

        pyautogui.FAILSAFE = False
        self._pyautogui = pyautogui

    def capture_screen_bgr(self) -> np.ndarray:
        screenshot = self._pyautogui.screenshot()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def random_click_in_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        padding: int = 2,
    ) -> Tuple[float, float]:
        if width <= 0 or height <= 0:
            target_x = float(x)
            target_y = float(y)
        else:
            inner_width = max(width - padding * 2, 1)
            inner_height = max(height - padding * 2, 1)
            target_x = float(random.randint(x + padding, x + padding + inner_width - 1))
            target_y = float(random.randint(y + padding, y + padding + inner_height - 1))

        start_x, start_y = self._pyautogui.position()
        steps = random.randint(self.move_steps[0], self.move_steps[1])
        for i in range(max(1, steps)):
            ratio = (i + 1) / steps
            nx = start_x + (target_x - start_x) * ratio + random.uniform(-1, 1)
            ny = start_y + (target_y - start_y) * ratio + random.uniform(-1, 1)
            self._pyautogui.moveTo(nx, ny)
            time.sleep(random.uniform(*self.step_delay_range))

        self._pyautogui.click(target_x, target_y, button="left")
        return target_x, target_y


def get_platform_adapter(preferred: str | None = None) -> PlatformAdapter:
    """根据当前系统或参数返回合适的适配器。"""

    preferred = (preferred or "auto").lower()

    def _is_mac() -> bool:
        return sys.platform == "darwin"

    def _is_windows() -> bool:
        return sys.platform.startswith("win")

    if preferred == "auto":
        if _is_mac():
            return _MacAdapter()
        if _is_windows():
            return _PyAutoGUIAdapter()
        # 其他平台优先尝试 PyAutoGUI
        return _PyAutoGUIAdapter()

    if preferred == "mac":
        if not _is_mac():
            raise RuntimeError("当前系统不是 macOS，无法使用 mac 适配器")
        return _MacAdapter()

    if preferred in {"win", "windows", "pyautogui"}:
        try:
            return _PyAutoGUIAdapter()
        except Exception as exc:  # pragma: no cover - 依赖可能不存在
            raise RuntimeError("初始化 Windows 适配器失败，请确保已安装 pyautogui") from exc

    raise RuntimeError(f"未知的平台选项: {preferred}")


__all__ = ["PlatformAdapter", "get_platform_adapter"]

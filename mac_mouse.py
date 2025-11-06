"""mac_mouse.py

封装基于 CoreGraphics 的鼠标操作工具函数。
"""

from __future__ import annotations

import ctypes
import random
import time
from ctypes import Structure, c_double, c_uint32, c_void_p
from ctypes import util
from typing import Tuple


class CGPoint(Structure):
    """表示二维平面上的一个点。"""

    _fields_ = [("x", c_double), ("y", c_double)]


class CGSize(Structure):
    """表示二维平面中的宽高尺寸。"""

    _fields_ = [("width", c_double), ("height", c_double)]


class CGRect(Structure):
    """表示带有原点和尺寸的矩形。"""

    _fields_ = [("origin", CGPoint), ("size", CGSize)]


def _objc_msg_send(restype, argtypes):
    libobjc_path = util.find_library("objc")
    if not libobjc_path:
        return None
    libobjc = ctypes.cdll.LoadLibrary(libobjc_path)
    fn = ctypes.CFUNCTYPE(restype, *argtypes)(("objc_msgSend", libobjc))
    return fn


_cg_path = util.find_library("ApplicationServices") or util.find_library("CoreGraphics")
_cg = ctypes.cdll.LoadLibrary(_cg_path) if _cg_path else None

kCGHIDEventTap = 0
kCGEventMouseMoved = 5
kCGEventLeftMouseDown = 1
kCGEventLeftMouseUp = 2
kCGMouseButtonLeft = 0

_display_scale = 1.0


if _cg is not None:
    _cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]
    _cg.CGWarpMouseCursorPosition.restype = None

    _cg.CGEventCreateMouseEvent.argtypes = [c_void_p, c_uint32, CGPoint, c_uint32]
    _cg.CGEventCreateMouseEvent.restype = c_void_p

    _cg.CGEventPost.argtypes = [c_uint32, c_void_p]
    _cg.CGEventPost.restype = None

    _cg.CFRelease.argtypes = [c_void_p]
    _cg.CFRelease.restype = None

    _cg.CGEventCreate.argtypes = [c_void_p]
    _cg.CGEventCreate.restype = c_void_p

    _cg.CGEventGetLocation.argtypes = [c_void_p]
    _cg.CGEventGetLocation.restype = CGPoint

    try:
        _cg.CGMainDisplayID.argtypes = []
        _cg.CGMainDisplayID.restype = c_uint32
        _cg.CGDisplayPixelsWide.argtypes = [c_uint32]
        _cg.CGDisplayPixelsWide.restype = c_uint32
        _cg.CGDisplayPixelsHigh.argtypes = [c_uint32]
        _cg.CGDisplayPixelsHigh.restype = c_uint32
    except Exception:
        pass

    try:
        msg_v = _objc_msg_send(c_void_p, (c_void_p, c_void_p))
        msg_f = _objc_msg_send(c_double, (c_void_p, c_void_p))
        if msg_v and msg_f:
            libobjc = ctypes.cdll.LoadLibrary(util.find_library("objc"))
            libobjc.objc_getClass.restype = c_void_p
            libobjc.objc_getClass.argtypes = [c_void_p]
            libobjc.sel_registerName.restype = c_void_p
            libobjc.sel_registerName.argtypes = [c_void_p]

            NSScreen = libobjc.objc_getClass(b"NSScreen")
            if NSScreen:
                main_screen = msg_v(NSScreen, libobjc.sel_registerName(b"mainScreen"))
                if main_screen:
                    scale = msg_f(main_screen, libobjc.sel_registerName(b"backingScaleFactor"))
                    if scale:
                        _display_scale = float(scale)
    except Exception:
        pass


def get_display_scale() -> float:
    """返回当前主显示器的缩放比例。"""

    return _display_scale


def get_mouse_position() -> Tuple[int, int]:
    """获取当前鼠标坐标。

    Returns:
        Tuple[int, int]: 鼠标的屏幕坐标 (x, y)。
    """

    if _cg is None:
        return (0, 0)
    event_ref = _cg.CGEventCreate(None)
    location = _cg.CGEventGetLocation(event_ref)
    _cg.CFRelease(event_ref)
    return (int(location.x), int(location.y))


def move_mouse(x: float, y: float) -> None:
    """将鼠标移动到指定坐标。

    Args:
        x (float): 目标坐标的 x 值。
        y (float): 目标坐标的 y 值。
    """

    if _cg is None:
        return
    _cg.CGWarpMouseCursorPosition(CGPoint(float(x), float(y)))


def left_click(x: float, y: float) -> None:
    """在指定坐标执行一次左键点击。

    Args:
        x (float): 点击位置的 x 坐标。
        y (float): 点击位置的 y 坐标。
    """

    if _cg is None:
        return
    down_event = _cg.CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, CGPoint(float(x), float(y)), kCGMouseButtonLeft)
    _cg.CGEventPost(kCGHIDEventTap, down_event)
    _cg.CFRelease(down_event)

    up_event = _cg.CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, CGPoint(float(x), float(y)), kCGMouseButtonLeft)
    _cg.CGEventPost(kCGHIDEventTap, up_event)
    _cg.CFRelease(up_event)


def random_click_in_rect(
    x: int,
    y: int,
    width: int,
    height: int,
    padding: int = 2,
    steps_range: Tuple[int, int] = (6, 15),
    step_delay_range: Tuple[float, float] = (0.01, 0.03),
) -> Tuple[float, float]:
    """在给定矩形内随机选择一个点并模拟点击。

    Args:
        x (int): 矩形左上角的 x 坐标。
        y (int): 矩形左上角的 y 坐标。
        width (int): 矩形的宽度像素值。
        height (int): 矩形的高度像素值。
        padding (int, optional): 在矩形内部向内偏移的像素，以避免点击边缘。默认值为 2。
        steps_range (Tuple[int, int], optional): 平滑移动时的步数范围 (最小步数, 最大步数)。默认值为 (6, 15)。
        step_delay_range (Tuple[float, float], optional): 每一步之间随机延迟的范围 (秒)。默认值为 (0.01, 0.03)。

    Returns:
        Tuple[float, float]: 真实鼠标点击的坐标 (x, y)。
    """

    if width <= 0 or height <= 0:
        return float(x), float(y)

    inner_width = max(width - padding * 2, 1)
    inner_height = max(height - padding * 2, 1)

    rx = random.randint(x + padding, x + padding + inner_width - 1)
    ry = random.randint(y + padding, y + padding + inner_height - 1)

    target_x = rx / _display_scale
    target_y = ry / _display_scale

    steps = random.randint(max(1, steps_range[0]), max(steps_range[0], steps_range[1]))
    start_x, start_y = get_mouse_position()

    for i in range(steps):
        ratio = (i + 1) / steps
        nx = start_x + (target_x - start_x) * ratio + random.uniform(-1, 1)
        ny = start_y + (target_y - start_y) * ratio + random.uniform(-1, 1)
        move_mouse(nx, ny)
        time.sleep(random.uniform(*step_delay_range))

    left_click(target_x, target_y)
    return target_x, target_y


__all__ = [
    "CGPoint",
    "CGSize",
    "CGRect",
    "get_display_scale",
    "get_mouse_position",
    "move_mouse",
    "left_click",
    "random_click_in_rect",
]



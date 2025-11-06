import argparse
import json
import os
import random
import time

import cv2

from platform_adapter import get_platform_adapter
from vision_utils import find_template_matches, find_text_boxes


def _normalize_targets(raw_target):
    if raw_target is None:
        raise ValueError("OCR 步骤缺少 target 字段")
    if isinstance(raw_target, str):
        targets = [t.strip() for t in raw_target.split('|') if t.strip()]
    elif isinstance(raw_target, list):
        targets = [str(t).strip() for t in raw_target if str(t).strip()]
    else:
        raise ValueError("OCR 步骤的 target 必须是字符串或字符串数组")
    if not targets:
        raise ValueError("OCR 步骤的 target 不能为空")
    return targets


def _load_template(step_copy, args, idx):
    tpl_path = step_copy.get('template') or args.template or './image.png'
    tpl_path = os.path.abspath(tpl_path)
    tpl_img = cv2.imread(tpl_path)
    if tpl_img is None:
        raise ValueError(f"第 {idx} 个步骤无法加载模板: {tpl_path}")
    step_copy['_template_image'] = tpl_img
    step_copy['_template_path'] = tpl_path
    step_copy['_tpl_thresh'] = float(step_copy.get('tpl_thresh', args.tpl_thresh))


def _prepare_steps(raw_steps, args):
    try:
        steps = json.loads(raw_steps)
    except json.JSONDecodeError as exc:
        raise ValueError(f"无法解析 steps JSON: {exc}") from exc

    if not isinstance(steps, list) or not steps:
        raise ValueError("steps 必须是非空数组")

    prepared = []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"第 {idx} 个步骤不是对象")

        mode = step.get('mode')
        if mode not in {'ocr', 'template', 'template_ocr'}:
            raise ValueError(f"第 {idx} 个步骤的 mode 无效: {mode}")

        step_copy = dict(step)
        step_copy['mode'] = mode

        if mode == 'ocr':
            step_copy['_targets'] = _normalize_targets(step_copy.get('target'))
            step_copy['_ocr_conf'] = int(step_copy.get('ocr_conf', args.ocr_conf))
            step_copy['_ocr_lang'] = step_copy.get('ocr_lang', args.ocr_lang)
        elif mode == 'template':
            _load_template(step_copy, args, idx)
        else:  # template_ocr
            step_copy['_targets'] = _normalize_targets(step_copy.get('target'))
            step_copy['_ocr_conf'] = int(step_copy.get('ocr_conf', args.ocr_conf))
            step_copy['_ocr_lang'] = step_copy.get('ocr_lang', args.ocr_lang)
            _load_template(step_copy, args, idx)

        prepared.append(step_copy)

    return prepared


def _wait_for_step(step, step_index, interval_range, adapter):
    mode = step['mode']
    while True:
        img = adapter.capture_screen_bgr()
        if mode == 'ocr':
            boxes = find_text_boxes(
                img,
                step['_targets'],
                conf_min=step['_ocr_conf'],
                lang=step['_ocr_lang']
            )
            if boxes:
                x, y, w, h, txt = boxes[0]
                rx, ry = adapter.random_click_in_rect(x, y, w, h)
                print(f"步骤 {step_index}: 找到文字 '{txt}' -> 点击 ({rx},{ry})")
                return
            else:
                print(f"步骤 {step_index}: 未找到目标文字 {step['_targets']}")
        elif mode == 'template':
            matches = find_template_matches(
                img,
                step['_template_image'],
                threshold=step['_tpl_thresh']
            )
            if matches:
                x, y, w, h, score = matches[0]
                rx, ry = adapter.random_click_in_rect(x, y, w, h)
                print(
                    f"步骤 {step_index}: 模板 '{os.path.basename(step['_template_path'])}' "
                    f"score={score:.2f} -> 点击 ({rx},{ry})"
                )
                return
            else:
                print(f"步骤 {step_index}: 未找到模板 '{os.path.basename(step['_template_path'])}'")
        else:  # template_ocr
            matches = find_template_matches(
                img,
                step['_template_image'],
                threshold=step['_tpl_thresh']
            )
            if matches:
                x, y, w, h, score = matches[0]
                region = img[y:y + h, x:x + w]
                boxes = find_text_boxes(
                    region,
                    step['_targets'],
                    conf_min=step['_ocr_conf'],
                    lang=step['_ocr_lang']
                )
                if boxes:
                    bx, by, bw, bh, txt = boxes[0]
                    rx, ry = adapter.random_click_in_rect(x + bx, y + by, bw, bh)
                    print(
                        f"步骤 {step_index}: 模板 '{os.path.basename(step['_template_path'])}' "
                        f"score={score:.2f} 内找到文字 '{txt}' -> 点击 ({rx},{ry})"
                    )
                    return
                else:
                    print(
                        f"步骤 {step_index}: 模板 '{os.path.basename(step['_template_path'])}' "
                        f"范围内未找到目标文字 {step['_targets']}"
                    )
            else:
                print(f"步骤 {step_index}: 未找到模板 '{os.path.basename(step['_template_path'])}'")

        time.sleep(random.uniform(*interval_range))


def _run_sequence(steps, interval_range, adapter):
    print(f"启动（CTRL+C 停止），多步骤模式，步骤数: {len(steps)}")
    step_index = 0
    try:
        while True:
            step = steps[step_index]
            human_index = step_index + 1
            print(f"开始步骤 {human_index}: 模式 {step['mode']}")
            _wait_for_step(step, human_index, interval_range, adapter)
            step_index = (step_index + 1) % len(steps)
    except KeyboardInterrupt:
        print("已停止")


def main(args):
    interval = (args.min_interval, args.max_interval)

    try:
        adapter = get_platform_adapter(args.platform)
    except RuntimeError as exc:
        print(str(exc))
        return

    if args.steps:
        try:
            steps = _prepare_steps(args.steps, args)
        except ValueError as exc:
            print(str(exc))
            return
        _run_sequence(steps, interval, adapter)
        return

    mode = args.mode
    print("启动（CTRL+C 停止），模式:", mode)
    tpl = None
    if mode == 'template':
        tpl_path = args.template or './image.png'
        if not args.template:
            print("未指定 --template，默认使用 ./image.png")
        tpl = cv2.imread(tpl_path)
        if tpl is None:
            print("无法加载模板:", tpl_path)
            return

    try:
        while True:
            img = adapter.capture_screen_bgr()
            if mode == 'ocr':
                boxes = find_text_boxes(
                    img,
                    args.target.split('|'),
                    conf_min=args.ocr_conf,
                    lang=args.ocr_lang
                )
                if boxes:
                    x, y, w, h, txt = boxes[0]
                    rx, ry = adapter.random_click_in_rect(x, y, w, h)
                    print(f"找到文字 '{txt}' 区域 -> 点击坐标: ({rx},{ry})")
                else:
                    print("未找到目标文字")
            else:
                matches = find_template_matches(img, tpl, threshold=args.tpl_thresh)
                if matches:
                    x, y, w, h, score = matches[0]
                    rx, ry = adapter.random_click_in_rect(x, y, w, h)
                    print(f"模板匹配 score={score:.2f} -> 点击坐标: ({rx},{ry})")
                else:
                    print("未找到模板")
            time.sleep(random.uniform(*interval))
    except KeyboardInterrupt:
        print("已停止")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['ocr', 'template'], default='ocr')
    p.add_argument('--target', help='OCR 模式下的关键词，多词用 | 分隔', default='购买')
    p.add_argument('--template', help='模板图片路径（PNG/JPG）')
    p.add_argument('--min_interval', type=float, default=0.8)
    p.add_argument('--max_interval', type=float, default=1.6)
    p.add_argument('--tpl_thresh', type=float, default=0.86)
    p.add_argument('--ocr_conf', type=int, default=60)
    p.add_argument('--ocr_lang', default='chi_sim+eng', help='pytesseract 识别语言，默认中英文')
    p.add_argument(
        '--steps',
        help='JSON 数组，定义多步骤操作，例如: [{"mode":"ocr","target":"开始"},{"mode":"template","template":"./ok.png"}]'
    )
    p.add_argument('--platform', default='auto', help='选择平台适配器: auto / mac / win / windows / pyautogui')
    args = p.parse_args()
    main(args)

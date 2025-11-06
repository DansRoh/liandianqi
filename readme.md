# 自动点击器

## 环境准备
- Python 3.9 及以上
- 建议使用虚拟环境管理依赖
- Windows 需额外安装 `pyautogui`

### 安装依赖
```bash
pip install opencv-python pytesseract pillow numpy pyautogui
```

> 如需使用 OCR，请确保已安装 Tesseract-OCR，并根据实际安装路径配置 `pytesseract.pytesseract.tesseract_cmd`。

## 运行命令

### OCR 模式
```bash
python auto_clicker_mac.py --mode ocr --target 购买
```

### 图片匹配模式
```bash
python auto_clicker_mac.py --mode template --template image.png
```

### 多步骤循环模式
```bash
python auto_clicker_mac.py \
  --steps '[{"mode":"ocr","target":"按钮1"},{"mode":"template","template":"./image.png"}]'
```
- `steps` 为 JSON 数组；程序会按照顺序依次执行每个步骤。
- 某一步骤匹配成功并点击后，才会进入下一步；若一直未匹配到，会持续重试。
- 所有步骤完成后，会回到第一步继续循环执行。
- 支持 `template_ocr` 步骤：先在指定模板位置匹配图片，再在匹配范围内识别文字，仅当文字满足条件时才点击。

#### `template_ocr` 示例
```bash
python auto_clicker_mac.py \
  --steps '[{"mode":"template_ocr","template":"./panel.png","target":"开始"}]'
```
- 将只在 `panel.png` 匹配区域内监听文字“开始”，一旦识别成功立即点击。

### 平台选择
```bash
python auto_clicker_mac.py --platform auto  # 自动选择
python auto_clicker_mac.py --platform mac   # 强制 macOS 适配器
python auto_clicker_mac.py --platform win   # 强制 Windows/PyAutoGUI 适配器
```
- 默认 `auto` 会在 macOS 上使用 CoreGraphics 方案，在 Windows/其他平台上使用 PyAutoGUI。
- 如使用 Windows，请确保已安装 `pyautogui` 并授予屏幕录制/控制权限。

更多命令参数可使用 `python auto_clicker_mac.py --help` 查看。



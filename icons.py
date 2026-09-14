"""라벨 한 글자를 트레이 아이콘(HICON)으로 렌더링한다."""
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = 32
ANSWER_BG = (24, 128, 56, 255)   # 진녹색: 정답 아이콘
MAIN_BG = (60, 60, 60, 255)      # 진회색: 메인/상태 아이콘
FG = (255, 255, 255, 255)
_FONT_PATH = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def _font(size: int):
    if _FONT_PATH.exists():
        return ImageFont.truetype(str(_FONT_PATH), size)
    return ImageFont.load_default(size)


def render_image(label: str, bg=ANSWER_BG) -> Image.Image:
    """32×32 RGBA: 둥근 배경 위에 흰 굵은 글자 하나."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, ICON_SIZE - 1, ICON_SIZE - 1), radius=6, fill=bg)
    font = _font(30)
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    x = (ICON_SIZE - (right - left)) / 2 - left
    y = (ICON_SIZE - (bottom - top)) / 2 - top
    draw.text((x, y), label, font=font, fill=FG)
    return img


def image_to_hicon(img: Image.Image) -> int:
    """PIL 이미지 → HICON 핸들. 사용 후 destroy_hicon()으로 해제."""
    import pywintypes
    import win32con
    import win32gui

    fd, path = tempfile.mkstemp(suffix=".ico")
    os.close(fd)
    try:
        img.save(path, format="ICO", sizes=[(ICON_SIZE, ICON_SIZE)])
        try:
            hicon = win32gui.LoadImage(
                0, path, win32con.IMAGE_ICON, 0, 0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
            )
        except pywintypes.error as e:
            raise RuntimeError(f"HICON 생성 실패: {e}") from e
    finally:
        os.remove(path)
    return hicon


def destroy_hicon(hicon: int) -> None:
    import win32gui

    if hicon:
        win32gui.DestroyIcon(hicon)

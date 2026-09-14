import pytest
from PIL import Image

from icons import ICON_SIZE, MAIN_BG, ANSWER_BG, render_image


@pytest.mark.parametrize("label", list("123456789") + list("ㄱㄴㄷㄹㅁ") + ["Q", "…", "-", "!"])
def test_renders_supported_labels_at_icon_size(label):
    img = render_image(label)
    assert isinstance(img, Image.Image)
    assert img.size == (ICON_SIZE, ICON_SIZE)
    assert img.mode == "RGBA"


def test_unknown_char_still_renders():
    assert render_image("Z").size == (ICON_SIZE, ICON_SIZE)


def test_answer_and_main_backgrounds_differ():
    answer = render_image("1", bg=ANSWER_BG)
    main = render_image("Q", bg=MAIN_BG)
    assert answer.getpixel((2, ICON_SIZE // 2)) != main.getpixel((2, ICON_SIZE // 2))


def test_glyph_is_drawn():
    img = render_image("1")
    # 배경 위에 흰 글자 픽셀이 실제로 그려져야 함
    pixels = list(img.get_flattened_data())
    assert any(p[0] > 200 and p[1] > 200 and p[2] > 200 for p in pixels)

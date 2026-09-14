"""트레이에 Q 아이콘을 띄우고, 좌클릭하면 1·3·4 아이콘을 추가한다."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from icons import ANSWER_BG, MAIN_BG, image_to_hicon, render_image  # noqa: E402
from tray import TrayManager  # noqa: E402

tray = None


def on_click():
    tray.remove_all_except(0)
    for i, label in enumerate(reversed(["1", "3", "4"]), start=1):
        tray.add(i, image_to_hicon(render_image(label, ANSWER_BG)), f"정답 {label}")


tray = TrayManager(
    on_left_click=on_click,
    menu=[("지우기", lambda: tray.remove_all_except(0)), ("종료", lambda: tray.quit())],
)
tray.add(0, image_to_hicon(render_image("Q", MAIN_BG)), "Tray Quiz Solver")
tray.run()

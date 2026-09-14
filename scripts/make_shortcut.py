r"""바탕화면에 'Tray Quiz Solver' 바로가기를 만든다 (pythonw main.py, 아이콘 포함).

    python scripts/make_shortcut.py

- app.ico: Q 아이콘을 16/32/48/256px로 렌더링해 프로젝트 루트에 저장
- 바로가기: 바탕화면\Tray Quiz Solver.lnk → pythonw.exe main.py (작업 폴더 = 프로젝트 루트)
바로가기를 작업 표시줄에 고정하려면 만들어진 .lnk를 우클릭 → "작업 표시줄에 고정".
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import win32com.client  # noqa: E402

from icons import MAIN_BG, render_image  # noqa: E402

ICO_PATH = ROOT / "app.ico"
SHORTCUT_NAME = "Tray Quiz Solver.lnk"


def make_ico() -> pathlib.Path:
    sizes = [(256, 256), (48, 48), (32, 32), (16, 16)]
    frames = [render_image("Q", MAIN_BG, size=s[0]) for s in sizes]
    frames[0].save(ICO_PATH, format="ICO", sizes=sizes, append_images=frames[1:])
    return ICO_PATH


def make_shortcut(ico: pathlib.Path) -> pathlib.Path:
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = pathlib.Path(shell.SpecialFolders("Desktop"))
    lnk_path = desktop / SHORTCUT_NAME
    pythonw = pathlib.Path(sys.executable).with_name("pythonw.exe")

    lnk = shell.CreateShortcut(str(lnk_path))
    lnk.TargetPath = str(pythonw)
    lnk.Arguments = f'"{ROOT / "main.py"}"'
    lnk.WorkingDirectory = str(ROOT)
    lnk.IconLocation = f"{ico},0"
    lnk.Description = "트레이 퀴즈 솔버 실행"
    lnk.Save()
    return lnk_path


if __name__ == "__main__":
    ico = make_ico()
    lnk = make_shortcut(ico)
    print(f"아이콘: {ico}")
    print(f"바로가기: {lnk}")

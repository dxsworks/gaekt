# 트레이 퀴즈 솔버 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 트레이 아이콘 좌클릭 → 주 모니터 캡처 → Gemini가 옳은 선지 판별 → 정답 라벨 하나당 트레이 아이콘 하나를 띄우는 Windows 상주 앱.

**Architecture:** `pywin32`로 숨김 창 하나를 만들고 `Shell_NotifyIcon`으로 아이콘을 ID별로 추가/수정/삭제한다(`tray.py`). 클릭이 오면 워커 스레드가 `capture.py` → `solver.py` 순으로 실행하고, 결과 라벨을 `icons.py`로 렌더링해 트레이에 추가한다(`main.py`). 순수 로직(파싱, 렌더링, 설정)은 GUI와 분리해 pytest로 검증한다.

**Tech Stack:** Python 3.14, pywin32 312, Pillow 12, mss 10, google-genai 2.22, pytest 9. 스펙: `docs/superpowers/specs/2026-09-14-tray-quiz-solver-design.md`

**환경 메모 (구현자 필독):**
- 이미 설치됨: google-genai, Pillow, pytest. 설치 필요: pywin32, mss (Task 1에서 설치)
- 기본 모델은 `gemini-3.8-flash` (2026-09-14 기준 공식 문서상 최신 안정 Flash). `config.json`으로 덮어쓸 수 있음
- 폰트: `C:\Windows\Fonts\malgunbd.ttf` 존재 확인됨
- 모든 명령은 프로젝트 루트 `C:\6th`에서 실행. 셸은 PowerShell 또는 Git Bash 둘 다 가능
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` 한 줄 추가

---

## File Structure

```
C:\6th\
├── main.py            # 진입점 + App 클래스 (클릭 → 캡처 → 풀이 → 아이콘 갱신 조율)
├── tray.py            # TrayManager: Win32 트레이 아이콘 추가/수정/삭제, 클릭 콜백, 메뉴, 메시지 루프
├── icons.py           # render_image(label) -> PIL.Image, image_to_hicon(img) -> HICON, destroy_hicon
├── capture.py         # capture_primary() -> PNG bytes
├── solver.py          # PROMPT, parse_response(text) -> list[str], solve(png, cfg) -> list[str]
├── config.py          # Config 데이터클래스, load_config(), ConfigError
├── config.example.json
├── requirements.txt
├── README.md
├── .gitignore
├── scripts/tray_smoke.py   # 트레이 수동 확인용
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_solver.py
    ├── test_icons.py
    └── test_capture.py
```

각 모듈은 한 가지 책임만 갖는다. `tray.py`와 `main.py`는 실제 화면이 필요해 수동 테스트, 나머지는 pytest.

---

### Task 1: 프로젝트 골격 + 의존성

**Files:**
- Create: `requirements.txt`, `.gitignore`, `config.example.json`, `tests/__init__.py`

- [ ] **Step 1: requirements.txt 작성**

```
pywin32>=312
Pillow>=12.0
mss>=10.0
google-genai>=2.22
pytest>=9.0
```

- [ ] **Step 2: .gitignore 작성**

```
__pycache__/
*.pyc
.pytest_cache/
config.json
app.log
*.ico
```

- [ ] **Step 3: config.example.json 작성**

```json
{
  "api_key": "여기에_GEMINI_API_KEY",
  "model": "gemini-3.8-flash"
}
```

- [ ] **Step 4: tests 패키지 생성**

빈 파일 `tests/__init__.py` 생성.

- [ ] **Step 5: 의존성 설치**

Run: `pip install -r requirements.txt`
Expected: 마지막 줄에 `Successfully installed mss-10.x pywin32-312` (이미 설치된 것은 "Requirement already satisfied")

- [ ] **Step 6: pywin32 임포트 확인**

Run: `python -c "import win32gui, win32con, mss; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore config.example.json tests/__init__.py
git commit -m "chore: project scaffold and dependencies"
```

---

### Task 2: config.py — 설정 로드

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config.py`:
```python
import json
import pytest

from config import Config, ConfigError, load_config


def test_loads_key_and_model_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "file-key", "model": "m-file"}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg == Config(api_key="file-key", model="m-file")


def test_file_key_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "file-key"}), encoding="utf-8")
    assert load_config(p).api_key == "file-key"


def test_env_key_used_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    cfg = load_config(tmp_path / "nope.json")
    assert cfg.api_key == "env-key"
    assert cfg.model == "gemini-3.8-flash"


def test_default_model_when_file_has_only_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "k"}), encoding="utf-8")
    assert load_config(p).model == "gemini-3.8-flash"


def test_error_when_no_key_anywhere(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_error_when_file_is_not_json(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: 구현**

`config.py`:
```python
"""config.json 또는 환경변수에서 Gemini 설정을 읽는다."""
import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_PATH = Path(__file__).with_name("config.json")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str = DEFAULT_MODEL


def load_config(path: Path | None = None) -> Config:
    """config.json(api_key, model) → 환경변수 GEMINI_API_KEY 순으로 읽는다."""
    path = DEFAULT_PATH if path is None else Path(path)
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(f"{path.name} 파싱 실패: {e}") from e
        if not isinstance(data, dict):
            raise ConfigError(f"{path.name}은 JSON 객체여야 합니다")

    api_key = data.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ConfigError("API 키 없음: config.json의 api_key 또는 환경변수 GEMINI_API_KEY 필요")

    model = data.get("model") or DEFAULT_MODEL
    return Config(api_key=api_key, model=model)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: load Gemini config from config.json or env"
```

---

### Task 3: solver.py — 응답 파싱 (순수 함수)

**Files:**
- Create: `solver.py`
- Test: `tests/test_solver.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_solver.py`:
```python
import pytest

from solver import SolverError, parse_response


def test_parses_numeric_labels():
    assert parse_response('{"correct": ["1", "3", "4"]}') == ["1", "3", "4"]


def test_sorts_numeric_labels_and_dedupes():
    assert parse_response('{"correct": ["4", "1", "3", "1"]}') == ["1", "3", "4"]


def test_normalizes_circled_numbers_and_ints():
    assert parse_response('{"correct": ["①", "③", 5]}') == ["1", "3", "5"]


def test_parses_and_sorts_jamo_labels():
    assert parse_response('{"correct": ["ㄷ", "ㄱ"]}') == ["ㄱ", "ㄷ"]


def test_empty_list_is_valid():
    assert parse_response('{"correct": []}') == []


def test_strips_markdown_fence():
    assert parse_response('```json\n{"correct": ["2"]}\n```') == ["2"]


@pytest.mark.parametrize("bad", [
    "not json",
    '{"answer": ["1"]}',
    '{"correct": "1"}',
    '{"correct": [{"a": 1}]}',
    '{"correct": ["hello"]}',
    "",
])
def test_rejects_malformed(bad):
    with pytest.raises(SolverError):
        parse_response(bad)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_solver.py -v`
Expected: `ModuleNotFoundError: No module named 'solver'`

- [ ] **Step 3: 구현 (parse_response만)**

`solver.py`:
```python
"""Gemini에게 캡처 이미지를 보내 옳은 선지 라벨을 받아온다."""
import json
import re

from config import Config

PROMPT = """화면 캡처에는 문제 지문 없이 선지(보기)만 있다.
각 선지는 독립된 서술문이다. 각 서술문이 참인지 거짓인지 스스로 판단해서
참인 선지만 골라라. 참인 선지가 여러 개일 수 있고, 하나도 없을 수도 있다.

라벨은 화면에 표시된 그대로 사용한다:
- 숫자 라벨(1, 2, 3, ... 또는 ①, ②, ③, ...)은 "1", "2", "3" 형식으로
- 한글 자모 라벨(ㄱ, ㄴ, ㄷ, ㄹ, ...)은 "ㄱ", "ㄴ" 형식으로

출력은 다음 JSON 객체 하나만, 다른 텍스트 없이:
{"correct": ["1", "3"]}
"""

_CIRCLED = {c: str(i + 1) for i, c in enumerate("①②③④⑤⑥⑦⑧⑨⑩")}
_JAMO_ORDER = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class SolverError(Exception):
    pass


def _normalize(label) -> str:
    if isinstance(label, bool) or not isinstance(label, (str, int)):
        raise SolverError(f"라벨 형식 오류: {label!r}")
    s = str(label).strip()
    s = _CIRCLED.get(s, s)
    if s.isdigit() or s in _JAMO_ORDER:
        return s
    raise SolverError(f"알 수 없는 라벨: {label!r}")


def _sort_key(label: str):
    if label.isdigit():
        return (0, int(label))
    return (1, _JAMO_ORDER.index(label))


def parse_response(text: str) -> list[str]:
    """Gemini 응답 텍스트 → 정렬·중복제거된 라벨 리스트. 형식이 어긋나면 SolverError."""
    cleaned = _FENCE.sub("", (text or "").strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise SolverError(f"JSON 아님: {cleaned[:80]!r}") from e
    if not isinstance(data, dict) or not isinstance(data.get("correct"), list):
        raise SolverError(f"'correct' 리스트 없음: {cleaned[:80]!r}")
    labels = {_normalize(x) for x in data["correct"]}
    return sorted(labels, key=_sort_key)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_solver.py -v`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add solver.py tests/test_solver.py
git commit -m "feat: parse Gemini answer JSON into sorted labels"
```

---

### Task 4: solver.py — Gemini 호출

**Files:**
- Modify: `solver.py` (import 추가 + 파일 끝에 `solve` 추가)
- Test: `tests/test_solver.py` (추가)

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_solver.py` 끝에 추가:
```python
from types import SimpleNamespace

import solver
from config import Config


def test_solve_sends_image_and_prompt_and_parses(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return SimpleNamespace(text='{"correct": ["2", "5"]}')

    class FakeClient:
        def __init__(self, *, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    monkeypatch.setattr(solver.genai, "Client", FakeClient)

    result = solver.solve(b"\x89PNG-fake", Config(api_key="k", model="m"))

    assert result == ["2", "5"]
    assert captured["api_key"] == "k"
    assert captured["model"] == "m"
    assert captured["config"].response_mime_type == "application/json"
    image_part, prompt = captured["contents"]
    assert image_part.inline_data.mime_type == "image/png"
    assert image_part.inline_data.data == b"\x89PNG-fake"
    assert prompt == solver.PROMPT


def test_solve_wraps_api_errors(monkeypatch):
    def boom(**kw):
        raise RuntimeError("boom")

    class FakeClient:
        def __init__(self, *, api_key):
            self.models = SimpleNamespace(generate_content=boom)

    monkeypatch.setattr(solver.genai, "Client", FakeClient)
    with pytest.raises(solver.SolverError, match="boom"):
        solver.solve(b"png", Config(api_key="k"))
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_solver.py -v -k solve`
Expected: `AttributeError: module 'solver' has no attribute 'genai'`

- [ ] **Step 3: 구현 추가**

`solver.py` 상단 import 블록에 추가 (`from config import Config` 위):
```python
from google import genai
from google.genai import types
```

`solver.py` 끝에 추가:
```python
def solve(png_bytes: bytes, cfg: Config) -> list[str]:
    """캡처 PNG를 Gemini에 보내 옳은 선지 라벨 리스트를 반환. 실패 시 SolverError."""
    try:
        client = genai.Client(api_key=cfg.api_key)
        response = client.models.generate_content(
            model=cfg.model,
            contents=[
                types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    except Exception as e:
        raise SolverError(f"Gemini 호출 실패: {e}") from e
    return parse_response(response.text)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_solver.py -v`
Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add solver.py tests/test_solver.py
git commit -m "feat: call Gemini with screenshot and parse answer"
```

---

### Task 5: icons.py — 라벨 아이콘 렌더링

**Files:**
- Create: `icons.py`
- Test: `tests/test_icons.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_icons.py`:
```python
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
    pixels = list(img.getdata())
    assert any(p[0] > 200 and p[1] > 200 and p[2] > 200 for p in pixels)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_icons.py -v`
Expected: `ModuleNotFoundError: No module named 'icons'`

- [ ] **Step 3: 구현**

`icons.py`:
```python
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
    font = _font(26)
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    x = (ICON_SIZE - (right - left)) / 2 - left
    y = (ICON_SIZE - (bottom - top)) / 2 - top
    draw.text((x, y), label, font=font, fill=FG)
    return img


def image_to_hicon(img: Image.Image) -> int:
    """PIL 이미지 → HICON 핸들. 사용 후 destroy_hicon()으로 해제."""
    import win32con
    import win32gui

    fd, path = tempfile.mkstemp(suffix=".ico")
    os.close(fd)
    try:
        img.save(path, format="ICO", sizes=[(ICON_SIZE, ICON_SIZE)])
        hicon = win32gui.LoadImage(
            0, path, win32con.IMAGE_ICON, 0, 0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )
    finally:
        os.remove(path)
    if not hicon:
        raise RuntimeError("HICON 생성 실패")
    return hicon


def destroy_hicon(hicon: int) -> None:
    import win32gui

    if hicon:
        win32gui.DestroyIcon(hicon)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_icons.py -v`
Expected: `21 passed`

- [ ] **Step 5: HICON 생성 수동 확인**

Run: `python -c "from icons import *; h = image_to_hicon(render_image('ㄱ')); print(h > 0); destroy_hicon(h)"`
Expected: `True`

- [ ] **Step 6: Commit**

```bash
git add icons.py tests/test_icons.py
git commit -m "feat: render single-label tray icons"
```

---

### Task 6: capture.py — 주 모니터 캡처

**Files:**
- Create: `capture.py`
- Test: `tests/test_capture.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_capture.py`:
```python
from capture import capture_primary


def test_returns_png_bytes():
    data = capture_primary()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 1000
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_capture.py -v`
Expected: `ModuleNotFoundError: No module named 'capture'`

- [ ] **Step 3: 구현**

`capture.py`:
```python
"""주 모니터 전체를 PNG 바이트로 캡처한다."""
import mss
import mss.tools


def capture_primary() -> bytes:
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # [0]은 전체 가상 화면, [1]이 주 모니터
        shot = sct.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_capture.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add capture.py tests/test_capture.py
git commit -m "feat: capture primary monitor as PNG"
```

---

### Task 7: tray.py — Win32 트레이 관리자

**Files:**
- Create: `tray.py`, `scripts/tray_smoke.py`

트레이는 자동 테스트가 불가능하므로 Step 2의 수동 스크립트로 검증한다.

- [ ] **Step 1: 구현**

`tray.py`:
```python
"""Shell_NotifyIcon으로 트레이 아이콘 여러 개를 ID별로 관리한다.

사용법:
    tray = TrayManager(on_left_click=fn, menu=[("지우기", fn2), ("종료", tray.quit)])
    tray.add(0, hicon, "툴팁"); tray.run()   # run()은 블로킹 메시지 루프
add/update/remove는 다른 스레드에서 호출해도 된다.
"""
import threading

import win32api
import win32con
import win32gui

from icons import destroy_hicon

_WM_TRAY = win32con.WM_USER + 20
_MENU_ID_BASE = 1000


class TrayManager:
    def __init__(self, on_left_click, menu):
        self._on_left_click = on_left_click
        self._menu = menu  # [(label, callback), ...]
        self._icons: dict[int, int] = {}  # id -> hicon
        self._lock = threading.Lock()

        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "TrayQuizSolver"
        wc.lpfnWndProc = {
            _WM_TRAY: self._on_tray_msg,
            win32con.WM_COMMAND: self._on_command,
            win32con.WM_DESTROY: self._on_destroy,
        }
        atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(
            atom, "TrayQuizSolver", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
        )

    # ---- 아이콘 관리 (스레드 안전) ----
    def add(self, icon_id: int, hicon: int, tip: str) -> None:
        with self._lock:
            self._icons[icon_id] = hicon
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self._nid(icon_id, hicon, tip))

    def update(self, icon_id: int, hicon: int, tip: str) -> None:
        with self._lock:
            old = self._icons.get(icon_id)
            self._icons[icon_id] = hicon
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self._nid(icon_id, hicon, tip))
            if old and old != hicon:
                destroy_hicon(old)

    def remove(self, icon_id: int) -> None:
        with self._lock:
            hicon = self._icons.pop(icon_id, None)
            if hicon is None:
                return
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, icon_id))
            destroy_hicon(hicon)

    def remove_all_except(self, keep_id: int) -> None:
        for icon_id in [i for i in self._icons if i != keep_id]:
            self.remove(icon_id)

    def _nid(self, icon_id, hicon, tip):
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        return (self.hwnd, icon_id, flags, _WM_TRAY, hicon, tip[:127])

    # ---- 메시지 루프 ----
    def run(self) -> None:
        win32gui.PumpMessages()

    def quit(self) -> None:
        win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def _on_tray_msg(self, hwnd, msg, wparam, lparam):
        icon_id = wparam
        if lparam == win32con.WM_LBUTTONUP and icon_id == 0:
            self._on_left_click()
        elif lparam == win32con.WM_RBUTTONUP and icon_id == 0:
            self._show_menu()
        return 0

    def _show_menu(self):
        menu = win32gui.CreatePopupMenu()
        for i, (label, _) in enumerate(self._menu):
            win32gui.AppendMenu(menu, win32con.MF_STRING, _MENU_ID_BASE + i, label)
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)  # 메뉴 밖 클릭 시 닫히게 함
        win32gui.TrackPopupMenu(
            menu, win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
            pos[0], pos[1], 0, self.hwnd, None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def _on_command(self, hwnd, msg, wparam, lparam):
        idx = win32api.LOWORD(wparam) - _MENU_ID_BASE
        if 0 <= idx < len(self._menu):
            self._menu[idx][1]()
        return 0

    def _on_destroy(self, hwnd, msg, wparam, lparam):
        for icon_id in list(self._icons):
            self.remove(icon_id)
        win32gui.PostQuitMessage(0)
        return 0
```

- [ ] **Step 2: 수동 확인 스크립트 작성 후 실행**

`scripts/tray_smoke.py`:
```python
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
```

Run: `python scripts/tray_smoke.py`
Expected (수동 확인):
- 트레이(또는 `^` 숨김 영역)에 회색 `Q` 아이콘이 나타남
- `Q` 좌클릭 → 녹색 `1` `3` `4` 아이콘이 나타남. **화면상 순서를 기록**: `1 3 4` 순이면 `reversed()`가 맞음, `4 3 1`이면 Task 8 Step 1의 `_show_answers`에서 `reversed(labels)`를 `labels`로 바꿈
- 우클릭 → 메뉴 `지우기`, `종료`. `지우기`로 정답 아이콘만 사라짐, `종료`로 모든 아이콘이 사라지고 프로세스 종료

- [ ] **Step 3: Commit**

```bash
git add tray.py scripts/tray_smoke.py
git commit -m "feat: Win32 tray manager with multiple dynamic icons"
```

---

### Task 8: main.py — 흐름 조율

**Files:**
- Create: `main.py`

- [ ] **Step 1: 구현**

`main.py`:
```python
"""트레이 퀴즈 솔버 진입점: Q 아이콘 좌클릭 → 캡처 → Gemini → 정답 라벨 아이콘."""
import logging
import threading
import traceback
from pathlib import Path

from capture import capture_primary
from config import ConfigError, load_config
from icons import ANSWER_BG, MAIN_BG, image_to_hicon, render_image
from solver import SolverError, solve
from tray import TrayManager

MAIN_ID = 0
LOG_PATH = Path(__file__).with_name("app.log")

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
)
log = logging.getLogger(__name__)


class App:
    def __init__(self):
        self._busy = threading.Lock()
        self.tray = TrayManager(
            on_left_click=self.on_click,
            menu=[("지우기", self.clear_answers), ("종료", self.quit)],
        )
        self.tray.add(MAIN_ID, image_to_hicon(render_image("Q", MAIN_BG)), "Tray Quiz Solver — 클릭하면 풀이")

    # ---- 트레이 콜백 (메시지 루프 스레드) ----
    def on_click(self):
        if not self._busy.acquire(blocking=False):
            return  # 처리 중 재클릭 무시
        threading.Thread(target=self._run, daemon=True).start()

    def clear_answers(self):
        self.tray.remove_all_except(MAIN_ID)

    def quit(self):
        self.tray.quit()

    # ---- 워커 스레드 ----
    def _run(self):
        try:
            self.clear_answers()
            self._set_main("…", "풀이 중…")
            cfg = load_config()
            labels = solve(capture_primary(), cfg)
            log.info("정답: %s", labels)
            self._show_answers(labels)
            self._set_main("Q" if labels else "-", "정답: " + (", ".join(labels) or "없음"))
        except (ConfigError, SolverError) as e:
            log.error("실패: %s", e)
            self._set_main("!", str(e))
        except Exception as e:
            log.error("예상치 못한 오류:\n%s", traceback.format_exc())
            self._set_main("!", f"오류: {e}")
        finally:
            self._busy.release()

    def _set_main(self, label: str, tip: str):
        self.tray.update(MAIN_ID, image_to_hicon(render_image(label, MAIN_BG)), tip)

    def _show_answers(self, labels: list[str]):
        # Windows는 새 아이콘을 왼쪽에 붙이므로 역순으로 추가해 화면상 정순이 되게 함
        # (Task 7 Step 2에서 확인한 실제 순서가 반대면 reversed()를 제거)
        for i, label in enumerate(reversed(labels), start=1):
            self.tray.add(i, image_to_hicon(render_image(label, ANSWER_BG)), f"정답 {label}")

    def run(self):
        self.tray.run()


if __name__ == "__main__":
    App().run()
```

- [ ] **Step 2: config.json 준비 후 실행**

`config.example.json`을 `config.json`으로 복사하고 실제 API 키를 넣는다 (사용자가 직접 — 구현자는 키를 요청만 하고 대신 입력하지 않는다). 그 후:

Run: `python main.py`
Expected (수동 확인):
1. 트레이에 `Q` 아이콘
2. 화면에 선지가 보이는 상태에서 `Q` 좌클릭 → `…`로 바뀜 → 몇 초 후 녹색 정답 아이콘들 + `Q` 복귀. `app.log`에 `정답: [...]` 기록
3. 정답이 없는 화면(예: 빈 바탕화면) → 아이콘 `-` 또는 `!`(모델이 형식 외 응답 시), 앱은 살아 있음
4. `config.json`의 키를 틀리게 바꾸고 클릭 → `!`, 툴팁에 원인. 다시 고치면 정상 동작
5. 처리 중 연타 → 한 번만 실행됨
6. 우클릭 `지우기`/`종료` 동작

- [ ] **Step 3: 전체 자동 테스트 재실행**

Run: `python -m pytest -v`
Expected: 마지막 줄 `42 passed` (config 6 + solver 14 + icons 21 + capture 1), failed 0

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: tray app wiring click → capture → Gemini → answer icons"
```

---

### Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 작성**

`README.md` (아래 내용 그대로; 바깥 펜스는 제외):

````markdown
# Tray Quiz Solver

트레이 아이콘을 클릭하면 주 모니터를 캡처해 Gemini가 옳은 선지를 고르고,
정답 라벨 하나당 트레이 아이콘 하나를 띄웁니다. (정답 1,3,4 → 아이콘 `1` `3` `4`)

## 설치

```
pip install -r requirements.txt
copy config.example.json config.json
```
`config.json`에 Gemini API 키를 넣습니다 (https://aistudio.google.com 에서 발급).
환경변수 `GEMINI_API_KEY`로 대신할 수도 있습니다. `model`은 생략 시 `gemini-3.8-flash`.

## 실행

```
python main.py
```
- 좌클릭 `Q`: 캡처 + 풀이
- 우클릭: `지우기` / `종료`
- 아이콘 의미: `Q` 대기, `…` 처리 중, `-` 정답 없음, `!` 오류(툴팁·`app.log` 참고)

## Windows 11에서 아이콘이 안 보일 때

Windows 11은 새 트레이 아이콘을 `^` 숨김 영역에 넣습니다.
**설정 → 개인 설정 → 작업 표시줄 → 기타 시스템 트레이 아이콘**에서 `python.exe`(Tray Quiz Solver)를 켜세요. 한 번만 하면 됩니다.

## 테스트

```
python -m pytest
```
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup and Windows 11 tray note"
```

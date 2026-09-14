"""트레이 퀴즈 솔버 진입점: Q 아이콘 좌클릭 → 캡처 → Gemini → 정답 라벨 아이콘."""
import ctypes

try:
    # Per-Monitor v2 DPI 인식. mss가 DPI 인식 상태를 건드리기 전에, 창을 만들기 전에 설정해야
    # 트레이 우클릭 메뉴가 고DPI 화면에서 흐릿하거나 잘못된 크기로 뜨지 않는다.
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

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
# 트레이는 새 아이콘을 왼쪽에 붙이므로 역순 추가. 화면에 4 3 1로 보이면 False로.
REVERSE_ORDER = True

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
)
log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)


class App:
    def __init__(self):
        self._busy = threading.Lock()
        self._cancel = threading.Event()
        self.tray = TrayManager(
            on_left_click=self.on_click,
            menu=[("지우기", self.clear_answers), ("종료", self.quit)],
        )
        self.tray.add(MAIN_ID, image_to_hicon(render_image("Q", MAIN_BG)), "Tray Quiz Solver — 클릭하면 풀이")

    # ---- 트레이 콜백 (메시지 루프 스레드) ----
    def on_click(self):
        if not self._busy.acquire(blocking=False):
            return  # 처리 중 재클릭 무시
        try:
            threading.Thread(target=self._run, daemon=True).start()
        except Exception:
            self._busy.release()
            raise

    def clear_answers(self):
        if self._busy.locked():
            self._cancel.set()  # 처리 중인 워커가 있으면 이후 단계를 건너뛰게 함
        self.tray.remove_all_except(MAIN_ID)

    def quit(self):
        if self._busy.locked():
            self._cancel.set()
        self.tray.quit()

    # ---- 워커 스레드 ----
    def _run(self):
        try:
            self._cancel.clear()
            self.tray.remove_all_except(MAIN_ID)
            self._set_main("…", "풀이 중…")
            cfg = load_config()
            labels = solve(capture_primary(), cfg)
            log.info("정답: %s", labels)
            if self._cancel.is_set():
                return  # 그 사이 지우기/종료가 눌림 → 결과를 반영하지 않음
            self._show_answers(labels)
            if self._cancel.is_set():
                return
            self._set_main("Q" if labels else "-", "정답: " + (", ".join(labels) or "없음"))
        except (ConfigError, SolverError) as e:
            log.error("실패: %s", e, exc_info=True)
            try:
                self._set_main("!", str(e))
            except Exception:
                log.exception("상태 아이콘 갱신 실패")
        except Exception as e:
            log.error("예상치 못한 오류:\n%s", traceback.format_exc())
            try:
                self._set_main("!", f"오류: {e}")
            except Exception:
                log.exception("상태 아이콘 갱신 실패")
        finally:
            self._busy.release()

    def _set_main(self, label: str, tip: str):
        self.tray.update(MAIN_ID, image_to_hicon(render_image(label, MAIN_BG)), tip)

    def _show_answers(self, labels: list[str]):
        # Windows는 새 아이콘을 왼쪽에 붙이므로 역순으로 추가해 화면상 정순이 되게 함
        ordered = reversed(labels) if REVERSE_ORDER else labels
        for i, label in enumerate(ordered, start=1):
            self.tray.add(i, image_to_hicon(render_image(label, ANSWER_BG)), f"정답 {label}")

    def run(self):
        self.tray.run()


if __name__ == "__main__":
    App().run()

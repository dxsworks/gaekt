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

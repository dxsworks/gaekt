"""주 모니터 전체를 PNG 바이트로 캡처한다."""
import mss
import mss.tools


def capture_primary() -> bytes:
    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # [0]은 전체 가상 화면, [1]이 주 모니터
        shot = sct.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)

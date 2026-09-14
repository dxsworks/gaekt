"""주 모니터 전체를 PNG 바이트로 캡처한다."""
import mss
import mss.tools


def capture_primary() -> bytes:
    with mss.MSS() as sct:
        # [0]은 전체 가상 화면. is_primary 플래그로 실제 주 모니터를 찾고, 없으면 [1]로 폴백.
        monitor = next((m for m in sct.monitors[1:] if m.get("is_primary")), sct.monitors[1])
        shot = sct.grab(monitor)
        return mss.tools.to_png(shot.rgb, shot.size)

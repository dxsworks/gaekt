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

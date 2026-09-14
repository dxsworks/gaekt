# Tray Quiz Solver

트레이 아이콘을 클릭하면 주 모니터를 캡처해 Gemini가 옳은 선지를 고르고,
정답 라벨 하나당 트레이 아이콘 하나를 띄웁니다. (정답 1,3,4 → 아이콘 `1` `3` `4`)

## 설치

```
pip install -r requirements.txt
copy config.example.json config.json   # PowerShell/cmd
cp config.example.json config.json     # Git Bash
```
`config.json`에 Gemini API 키를 넣습니다 (https://aistudio.google.com 에서 발급).
환경변수 `GEMINI_API_KEY`로 대신할 수도 있습니다. `model`은 생략 시 `gemini-3.5-flash`.

## 실행

```
pythonw main.py
```
콘솔 창 없이 백그라운드로 뜹니다. `python main.py`(콘솔 있음)로 실행하면 그 콘솔 창을 닫을 때
앱이 정리 없이 함께 죽으니 `pythonw`를 권장합니다.
- 좌클릭 `Q`: 캡처 + 풀이
- 우클릭: `지우기` / `종료`
- 아이콘 의미: `Q` 대기, `…` 처리 중, `-` 정답 없음, `!` 오류(툴팁·`app.log` 참고)
- 정답 아이콘이 `4 3 1`처럼 거꾸로 보이면 main.py의 `REVERSE_ORDER`를 `False`로 바꾸세요.

## Windows 11에서 아이콘이 안 보일 때

Windows 11은 새 트레이 아이콘을 `^` 숨김 영역에 넣습니다.
**설정 → 개인 설정 → 작업 표시줄 → 기타 시스템 트레이 아이콘**에서 `pythonw.exe`(Tray Quiz Solver)를 켜세요
(`pythonw main.py`로 실행했다면). 한 번만 하면 됩니다.

## 테스트

```
python -m pytest
```

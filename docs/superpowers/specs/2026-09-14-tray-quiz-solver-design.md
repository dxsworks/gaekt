# 트레이 퀴즈 솔버 — 설계

## 목적

Windows 시스템 트레이 아이콘을 클릭하면 주 모니터를 캡처해 Gemini API로 보내고,
화면에 있는 선지 중 "옳은 것"의 라벨을 **라벨 하나당 트레이 아이콘 하나**로 표시한다.
예: 정답이 `1, 3, 4`이면 트레이에 `1` `3` `4` 아이콘 3개가 나란히 뜬다.

## 확정된 요구사항

- 트리거: 메인 트레이 아이콘 **좌클릭**
- 캡처 범위: **주 모니터 전체**
- 화면에는 문제 지문 없이 **선지만** 있음. 각 선지는 독립된 서술문이며 참인 것만 고른다
- 선지 라벨: `1~5`(①②③ 형태 포함) 또는 `ㄱㄴㄷㄹ`. 화면에 표시된 라벨 그대로 반환
- 표시 방식: 정답 개수만큼 트레이 아이콘 생성, 각 아이콘에 라벨 한 글자
- 언어: Python
- Gemini 키: `config.json` 또는 환경변수 `GEMINI_API_KEY`. 기본 모델은 Flash 계열

## 구현 방식

`pywin32`로 `Shell_NotifyIcon`을 직접 호출한다. 숨김 창 하나에 여러 아이콘을 ID별로
추가/수정/삭제하며, 메시지 루프 하나에서 클릭을 받는다.
(`pystray`는 단일 아이콘 앱을 가정해 다중 아이콘 동적 생성이 불안정하므로 제외)

## 모듈

| 파일 | 역할 | 의존 |
|---|---|---|
| `main.py` | 진입점. 클릭 → 캡처 → 풀이 → 아이콘 갱신 흐름 조율. 워커 스레드에서 실행 | 아래 전부 |
| `tray.py` | `TrayManager`: `add(id, hicon, tip)`, `update(id, hicon, tip)`, `remove(id)`, `remove_all_except(id)`, 좌클릭/우클릭 콜백, 우클릭 메뉴, `run()` 메시지 루프 | pywin32 |
| `icons.py` | `render_label(text) -> HICON`: 32×32, 진한 배경 + 흰 굵은 글자(맑은 고딕 Bold). 상태 기호 `Q` `…` `-` `!`도 같은 함수로 | Pillow, pywin32 |
| `capture.py` | `capture_primary() -> bytes`: 주 모니터 PNG | mss |
| `solver.py` | `solve(png_bytes, cfg) -> list[str]`: Gemini 호출 + JSON 파싱. `parse_response(text) -> list[str]`는 순수 함수로 분리 | google-genai |
| `config.py` | `load_config() -> Config(api_key, model)`: `config.json` → 환경변수 순으로 읽음 | — |

`config.json` 예시:
```json
{ "api_key": "...", "model": "gemini-2.5-flash" }
```
(모델 이름은 구현 시점의 최신 Flash 모델로 확인해 기본값 지정)

## 동작 흐름

1. 실행 → 메인 아이콘 `Q` 표시 (ID 0). 우클릭 메뉴: `지우기`, `종료`
2. 좌클릭 → 이미 처리 중이면 무시. 아니면 워커 스레드 시작:
   1. 정답 아이콘(ID 1..N) 전부 삭제
   2. 메인 아이콘을 `…`로 변경
   3. `capture_primary()` → `solve()` → 라벨 리스트
   4. 라벨 리스트를 **역순**으로 순회하며 아이콘 추가 (Windows는 새 아이콘을 왼쪽에 붙이므로, 화면상 `1 3 4` 순서가 되게 함. 구현 시 실제 순서 확인)
   5. 메인 아이콘 `Q`로 복귀
3. 정답 아이콘은 다음 클릭 또는 `지우기` 메뉴까지 유지
4. `종료` → 아이콘 전부 삭제 후 프로세스 종료

## 오류 처리

| 상황 | 표시 |
|---|---|
| 정답 없음(빈 리스트) | 메인 아이콘 `-` |
| API 키 없음, 네트워크/API 오류, JSON 파싱 실패, 캡처 실패 | 메인 아이콘 `!`, 툴팁에 한 줄 원인 |
| 모든 오류 | `app.log`에 traceback 기록, 앱은 계속 실행되어 다음 클릭 가능 |

## Gemini 프롬프트

- 입력: PNG 이미지 + 텍스트 지시
- 지시 요지: 화면에 문제 지문 없이 선지만 있다. 각 선지를 독립된 서술문으로 판단해 **참인 것만** 고른다. 라벨은 화면에 표시된 그대로(`1`,`2`… 또는 `ㄱ`,`ㄴ`…; ①②③은 `1`,`2`,`3`으로 정규화) 반환. 출력은 `{"correct": ["1","3"]}` 형식 JSON만
- `response_mime_type="application/json"`으로 JSON 강제
- 파싱: `correct` 키의 문자열 리스트. 중복 제거, 화면 순서(숫자/자모 순) 정렬. 형식이 어긋나면 오류로 처리

## 아이콘 렌더링

- 32×32 RGBA (Windows가 16×16으로 축소해도 굵은 한 글자는 읽힘)
- 정답 아이콘: 진녹색 둥근 배경 + 흰 글자. 메인 아이콘: 진회색 배경으로 구분
- 폰트: `C:\Windows\Fonts\malgunbd.ttf`(맑은 고딕 Bold). 없으면 Pillow 기본 폰트로 폴백
- Pillow 이미지 → `.ico` 바이트 → `CreateIconFromResourceEx`로 HICON 생성. HICON은 아이콘 삭제 시 `DestroyIcon`

## 테스트

자동(pytest):
- `solver.parse_response`: 정상 JSON, 빈 리스트, `correct` 키 없음, JSON 아님, 중복/정렬
- `icons.render_image`: 지원 라벨 전부 32×32 이미지 반환, 미지원 문자도 예외 없이 렌더
- `capture.capture_primary`: 0바이트가 아닌 PNG 시그니처
- `config.load_config`: 파일 → 환경변수 우선순위, 둘 다 없으면 명시적 오류

수동:
- 트레이 아이콘 표시, 순서, 좌클릭 트리거, 우클릭 메뉴, 처리 중 재클릭 무시, 오류 시 `!` 표시

## 알려진 제약

- Windows 11은 새 트레이 아이콘을 기본적으로 숨김 영역에 넣는다. 최초 1회 설정 → 개인 설정 → 작업 표시줄 → "기타 시스템 트레이 아이콘"에서 이 앱(python.exe 또는 exe 이름)을 켜야 한다
- 단축키 트리거, 영역 선택 캡처, 다중 모니터는 범위 밖

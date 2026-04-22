# QuickStart

## 프로젝트 한줄 소개

Streamlit UI에서 주식 알람을 등록하고, 배치 스크립트가 조건을 검사한 뒤 메일로 통지하는 무료 중심의 비상업용 프로젝트다.

## 1. 실행 전 준비사항

| 항목 | 내용 |
| --- | --- |
| 운영체제 기준 | 현재 문서는 Windows PowerShell 기준 |
| 권장 Python | 프로젝트 폴더의 `.venv` 사용 권장 |
| 확인된 상태 | 시스템 Python 3.12에는 `streamlit` 미설치, `.venv`에서는 주요 패키지 import 가능 |
| 필수 외부 서비스 | Supabase, Gmail SMTP |
| 로컬 시크릿 | UI용 `.streamlit/secrets.toml`, 배치용 환경변수 필요 |

## 2. 처음 시작 순서

1. PowerShell에서 프로젝트 루트로 이동한다.
2. 가능하면 `.venv`를 활성화하거나 `.venv`의 Python을 직접 사용한다.
3. UI 작업은 `app.py`, 메일 작업은 `main.py`부터 본다.
4. 실제 시크릿은 로컬에만 넣고 문서/커밋에는 넣지 않는다.

## 3. 환경변수/시크릿 파일 일반 형식

### 3.1 Streamlit UI용 시크릿 예시

파일 위치 예시: `.streamlit/secrets.toml`

```toml
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"
```

### 3.2 배치 실행용 환경변수 예시

PowerShell 세션 예시:

```powershell
$env:EMAIL_USER = "YOUR_EMAIL_ADDRESS_HERE"
$env:EMAIL_PW = "YOUR_EMAIL_APP_PASSWORD_HERE"
$env:SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
$env:SUPABASE_KEY = "YOUR_SUPABASE_KEY_HERE"
```

### 3.3 GitHub Actions 시크릿 이름

저장소 워크플로 기준으로 아래 이름이 필요하다.

- `EMAIL_USER`
- `EMAIL_PW`
- `SUPABASE_URL`
- `SUPABASE_KEY`

## 4. 실행 방법

### 4.1 프로젝트 루트 이동

```powershell
Set-Location C:\Dev\40StockAlertProject
```

### 4.2 가상환경 사용

권장 1안:

```powershell
.\.venv\Scripts\Activate.ps1
```

실행 정책으로 막히면 현재 세션에서만 우회:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

권장 2안:

```powershell
.\.venv\Scripts\python.exe --version
```

### 4.3 UI 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저에서 표시된 로컬 주소로 접속한다.

### 4.4 메일 발송 배치 수동 실행

선행조건: 배치용 환경변수 설정 완료

```powershell
.\.venv\Scripts\python.exe main.py
```

### 4.5 GitHub Actions 자동 실행 참고

| 항목 | 내용 |
| --- | --- |
| 파일 | `.github/workflows/alert.yml` |
| 실행 방식 | 평일 장중 스케줄 + 수동 실행 |
| 현재 확인된 cron | 10분 간격 실행 |

## 5. 주요 폴더/파일 설명

| 경로 | 설명 | 작업 시작 포인트 |
| --- | --- | --- |
| `app.py` | 로그인, 회원가입, 알람 등록/관리 UI | 웹 디자인 개선 시작점 |
| `main.py` | 지표 계산, 조건 검사, 메일 발송 | 메일 디자인 개선 시작점 |
| `.github/workflows/alert.yml` | 자동 실행 설정 | 운영 주기 확인 |
| `.devcontainer/devcontainer.json` | Dev Container 실행 설정 | 컨테이너 기반 작업 참고 |
| `README.md` | 기존 개요 문서 | 최신 코드와 차이 확인 필요 |
| `Docs/2026-04-22/` | 현재 정리 문서 | 작업 기준 문서 |

## 6. UI 작업 시작 포인트

| 대상 | 바로 볼 위치 | 메모 |
| --- | --- | --- |
| 전체 페이지 톤 | `app.py` 상단 `st.set_page_config()` 이후 | 기본 레이아웃/페이지 제목 확인 |
| 로그인/회원가입 | 비로그인 탭 영역 | 첫인상 개선 대상 |
| 알람 등록 폼 | `alert_register_form` | 폼 구조, 설명, 버튼 스타일 개선 대상 |
| 알람 관리 화면 | `main_tab2` 영역 | 카드/상태 요약 개선 대상 |

### UI 작업 권장 순서

1. 현재 화면 캡처 저장
2. 상단 헤더/설명 블록 추가
3. 카드/버튼/폼 간격 규칙 정리
4. 등록/관리 화면의 정보 위계 재배치
5. 변경 후 캡처 저장

## 7. 메일 템플릿 작업 시작 포인트

| 대상 | 바로 볼 위치 | 메모 |
| --- | --- | --- |
| 발송 함수 | `main.py`의 `send_email()` | 현재 plain text만 사용 |
| 제목/본문 생성 | 알람 충족 후 `subject`, `body` 문자열 조합 구간 | 템플릿 분리 필요 |
| 발송 시점 | 조건 충족 후 `send_email()` 호출 구간 | HTML/텍스트 멀티파트 전환 후보 |

### 메일 작업 권장 순서

1. 현재 텍스트 메일 구조 정리
2. 제목/요약/조건/현재값/안내문 구조로 재설계
3. HTML 템플릿 추가
4. plain text 대체 본문 유지
5. 샘플 메일 캡처 저장

## 8. 주의사항

| 항목 | 주의사항 |
| --- | --- |
| 민감정보 | 실제 키, 비밀번호, 토큰, URL을 문서/커밋/스크린샷에 남기지 말 것 |
| 시크릿 파일 | `.streamlit/secrets.toml`은 로컬 전용으로 관리 |
| 실행 환경 | 시스템 Python이 아니라 `.venv` 기준으로 작업할 것 |
| 브랜드 명칭 | `StockSignalBot Pro`와 `QuantBot` 혼용 여부 확인 후 통일할 것 |
| 메일 테스트 | 실제 수신자에게 불필요한 발송이 가지 않도록 테스트 계정 사용 권장 |
| 범위 관리 | 알람 조건 고도화보다 UI/메일 디자인 개선을 우선 처리할 것 |

## 9. 실행을 전혀 모를 때 최소 가이드

아래 순서만 따라도 기본 진입이 가능하다.

1. `Set-Location C:\Dev\40StockAlertProject`
2. `.\.venv\Scripts\Activate.ps1`
3. UI 확인: `.\.venv\Scripts\python.exe -m streamlit run app.py`
4. 메일 배치 확인 전: 배치용 환경변수 4개를 먼저 세팅
5. 배치 확인: `.\.venv\Scripts\python.exe main.py`

UI 수정은 `app.py`, 메일 디자인 수정은 `main.py`부터 시작하면 된다.

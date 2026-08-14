# Classroom Chat

교실 내부 LAN 전용 실시간 채팅 웹 애플리케이션

---

## 1. 설치 및 실행

### 사전 조건
- Python 3.10 이상이 설치되어 있어야 합니다.
- Windows 기준으로 작성되었습니다.

### 설치

```powershell
# 프로젝트 폴더로 이동
cd C:\path\to\intel7-chat

# (선택) 가상환경 생성
python -m venv .venv
.venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버가 시작되면 같은 PC에서 브라우저로 http://localhost:8000 에 접속합니다.

---

## 2. 호스트 PC의 내부 IP 주소 확인 (Windows)

```powershell
ipconfig
```

출력 중 **이더넷 어댑터** 또는 **Wi-Fi 어댑터** 아래에 표시된  
`IPv4 주소 . . . : 192.168.x.x` 형태의 주소가 호스트 IP입니다.

예시:
```
이더넷 어댑터 이더넷:
   IPv4 주소 . . . . . . . . : 192.168.1.42
```

---

## 3. 다른 PC에서 접속하는 방법

호스트 PC와 **같은 Wi-Fi 또는 유선 LAN**에 연결된 다른 PC에서 브라우저 주소창에 아래를 입력합니다.

```
http://192.168.1.42:8000
```

(위 IP는 예시입니다. 2번에서 확인한 실제 IP로 바꾸세요.)

---

## 4. 접속이 안 될 때 확인 사항

1. **같은 네트워크인지 확인**: 호스트 PC와 접속하려는 PC가 같은 공유기(Wi-Fi 또는 유선)에 연결되어 있어야 합니다.
2. **IP 주소가 맞는지 재확인**: `ipconfig`로 다시 확인하세요.
3. **서버가 실행 중인지 확인**: 서버가 실행된 터미널에서 오류가 없는지 확인하세요.
4. **방화벽 확인** (다음 섹션 참고)

---

## 5. Windows Defender 방화벽 설정

접속이 안 될 경우 방화벽에서 8000 포트를 허용해야 합니다.

### 방법 A – PowerShell (관리자 권한)

```powershell
New-NetFirewallRule -DisplayName "Classroom Chat" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### 방법 B – GUI

1. `Windows Defender 방화벽` → **인바운드 규칙** → **새 규칙**
2. 규칙 유형: **포트** → TCP, 특정 포트: **8000**
3. 작업: **연결 허용**
4. 규칙 이름: `Classroom Chat` 등 원하는 이름 입력 후 완료

또는 Python 프로그램을 처음 실행할 때 Windows가 방화벽 허용 여부를 자동으로 물어보면 **허용**을 선택하세요.

---

## 6. 보안 주의사항

> ⚠️ **이 서버는 교실 내부 LAN 전용입니다.**
>
> - 공개 인터넷에 직접 노출하지 마세요.
> - 라우터의 포트 포워딩(외부 개방)을 설정하지 마세요.
> - 인증 없이 누구나 메시지를 볼 수 있으므로 민감한 정보는 입력하지 마세요.

---

## 7. 주요 설정 변경

| 항목 | 파일 | 변수 |
|------|------|------|
| 서비스 이름 | `app/main.py` | `SERVICE_NAME` |
| 메시지 보관 기간 | `app/database.py` | `MESSAGE_RETENTION_DAYS` |
| 닉네임 최대 길이 | `app/main.py` | `MAX_NICKNAME_LEN` |
| 메시지 최대 길이 | `app/main.py` | `MAX_CONTENT_LEN` |
| 만료 메시지 삭제 주기 | `app/main.py` | `CLEANUP_INTERVAL_SECONDS` |

---

## 8. 프로젝트 구조

```
intel7-chat/
├─ app/
│  ├─ __init__.py
│  ├─ main.py          ← FastAPI 서버, WebSocket, 라우터
│  ├─ database.py      ← SQLite CRUD, 메시지 만료 처리
│  ├─ templates/
│  │  └─ index.html    ← 메인 HTML 템플릿
│  └─ static/
│     ├─ style.css     ← 스타일시트
│     └─ app.js        ← 클라이언트 JavaScript
├─ data/
│  └─ chat.db          ← SQLite DB (서버 시작 시 자동 생성)
├─ requirements.txt
└─ README.md
```

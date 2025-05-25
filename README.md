# 🧠 SwingChat - ShinhanDS Hackday Project

AI 기반 인프라 운영 자동화 메신저 `SwingChat`입니다.  
Python + Flask 기반으로 구현되었으며, GPT-3.5 API를 활용해 명령어 기반 서버 상태 확인 및 로그 분석 기능을 제공합니다.

---

## 📦 필수 설치 프로그램 (Windows)

1. **Git 설치**
   - [Git 다운로드 링크](https://git-scm.com/download/win)
   - 설치 후 "Git Bash" 실행

2. **Python 설치 (버전 3.10 이상)**
   - [Python 다운로드 링크](https://www.python.org/downloads/)
   - 설치 시 `Add Python to PATH` 꼭 체크!

---

## 📥 프로젝트 다운로드 방법

### 방법 1. Git 사용
```bash
git clone https://github.com/ljsgold2001/shinhanDS_HACKDAY.git
cd shinhanDS_HACKDAY
```

### 방법 2. Git 없이 ZIP 다운로드
- 👉 [GitHub 레포 바로가기](https://github.com/ljsgold2001/shinhanDS_HACKDAY)
- 초록색 `Code` 버튼 클릭 → `Download ZIP`
- 압축 해제 후 `shinhanDS_HACKDAY` 폴더 열기

---

## ⚙️ 환경 구성 및 실행

### 1. 패키지 설치
```bash
pip install flask openai paramiko python-dotenv
```

### 2. `.env` 파일 생성 (프로젝트 루트에 위치)
```
OPENAI_API_KEY="sk-..."
SSH_USERNAME="root"
SSH_PASSWORD="your_password"
```

### 3. 실행 명령어 (Windows CMD 기준)
```bash
set FLASK_APP=app.py
flask run
```

서버 실행 후 [http://127.0.0.1:5000](http://127.0.0.1:5000) 접속

---

## 🛠️ 명령어 예시

```
!ping 192.168.0.1           → 서버 Ping 체크
!uptime 192.168.0.1         → 서버 업타임 확인
!disk 192.168.0.1           → 디스크 사용량
!log 192.168.0.1            → 로그 조회 후 GPT 요약
!log-detail 192.168.0.1     → 에러 필터링 로그 조회
!ps 192.168.0.1 python      → 프로세스 검색
```

---

## 📁 폴더 구조

```
shinhanDS_HACKDAY/
├── app.py              # Flask 백엔드
├── .env                # 환경변수 (절대 Git에 포함 금지)
├── templates/          # HTML 템플릿
├── static/             # 정적 이미지 파일
├── .gitignore
└── README.md
```

---

## 👥 Contributors
-  5조 팀원

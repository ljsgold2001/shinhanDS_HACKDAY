from flask import Flask, render_template, request, redirect, session, jsonify
import os
import re
import paramiko
from datetime import datetime
import platform
from dotenv import load_dotenv
from openai import OpenAI
import json

# 환경변수 로딩
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# FAQ 데이터 로딩
with open("data.json", "r", encoding="utf-8") as f:
    FAQ_DATA = json.load(f)

# OpenAI 클라이언트 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# SSH 자격증명
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")

# 사용자 정보
USER_DB = {
    "21071009": {
        "password": "123456",
        "company": "신한DS",
        "name": "고정훈"
    }
}

chat_logs = []

@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        userid = request.form["userid"]
        password = request.form["password"]
        company = request.form["company"]
        user = USER_DB.get(userid)
        if user and user["password"] == password and user["company"] == company:
            session["user"] = userid
            session["name"] = user["name"]
            return redirect("/home")
        else:
            return "로그인 실패", 401
    return render_template("login.html")

@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/login")
    chat_list = [{
        "id": "gpt",
        "title": "Swing AI",
        "last_message": chat_logs[-1]['content'] if chat_logs else "대화를 시작하세요!",
        "time": "방금 전",
        "avatar": "/static/ai_icon.png",
        "unread": 0
    }]
    return render_template("home.html", chats=chat_list)

@app.route("/chat/<room_id>")
def chat(room_id):
    if "user" not in session:
        return redirect("/login")
    return render_template("chat.html", room_id=room_id, name=session["name"], messages=chat_logs)

@app.route("/chat", methods=["POST"])
def chat_api():
    user_input = request.json.get("message")
    timestamp = datetime.now().strftime("%p %I:%M")
    chat_logs.append({"role": "user", "content": user_input, "timestamp": timestamp})

    def run_ping(ip):
        import subprocess
        try:
            flag = "-n" if platform.system().lower() == "windows" else "-c"
            return subprocess.check_output(["ping", flag, "1", ip], universal_newlines=True)
        except subprocess.CalledProcessError as e:
            return f"Ping 실패: 응답 없음 또는 목적지에 도달하지 못했습니다.\n{e.output}"
        except Exception as e:
            return f"Ping 실패: {str(e)}"

    def ssh_command(ip, command):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD, timeout=5)
            _, stdout, _ = ssh.exec_command(command)
            output = stdout.read().decode()
            ssh.close()
            return output
        except Exception as e:
            return f"명령어 실행 실패: {str(e)}"

    def fetch_logs(ip):
        return ssh_command(ip, "tail -n 50 /var/log/messages")

    def format_log_detail(logs):
        if "로그 조회 실패" in logs:
            return logs
        filtered = [line for line in logs.splitlines() if any(k in line.lower() for k in ["error", "fail", "warn", "denied", "retri", "timeout"])]
        if not filtered:
            filtered = logs.splitlines()[:5]
        return "📄 필터링 로그:\n" + "\n".join(filtered)

    # AI 분석용 함수들
    def analyze_ping_with_ai(text):
        prompt = f"다음은 ping 명령어의 결과입니다. 응답 여부와 지연 시간, 손실률을 기반으로 네트워크 상태를 간단히 진단해 주세요.\n\n{text}"
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 네트워크 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

    def analyze_uptime_with_ai(text):
        prompt = f"다음은 uptime 명령어의 출력입니다. 시스템 가동 시간과 부하 상태를 간단히 분석해 주세요.\n\n{text}"
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 리눅스 시스템 관리자입니다."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

    def analyze_disk_with_ai(text):
        prompt = f"다음은 df -h 명령어 결과입니다. 디스크 사용률을 요약하고 위험 구간이 있는지 판단해 주세요.\n\n{text}"
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 인프라 운영 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

    def analyze_ps_with_ai(text):
        prompt = f"다음은 ps 명령어 결과입니다. 주요 프로세스 상태를 분석해 주세요.\n\n{text}"
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 리눅스 프로세스 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

    def analyze_logs_with_ai(text):
        lines = text.strip().split("\n")
        key_lines = [line for line in lines if any(k in line.lower() for k in ["error", "fail", "warn", "denied", "retri", "timeout"])]
        summary = "\n".join(key_lines[:5] if key_lines else lines[:3])
        prompt = f"다음은 /var/log/messages 로그입니다. 에러/경고 등을 중심으로 핵심 내용을 요약해 주세요.\n\n{summary}"
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 인프라 운영 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

    # 명령어 매핑
    command_patterns = [
        (r'^!ping (\d+\.\d+\.\d+\.\d+)$', lambda ip: run_ping(ip)),
        (r'^!log (\d+\.\d+\.\d+\.\d+)$', lambda ip: format_log_detail(fetch_logs(ip))),
        (r'^!uptime (\d+\.\d+\.\d+\.\d+)$', lambda ip: ssh_command(ip, "uptime")),
        (r'^!disk (\d+\.\d+\.\d+\.\d+)$', lambda ip: ssh_command(ip, "df -h")),
        (r'^!ps (\d+\.\d+\.\d+\.\d+) (.+)$', lambda ip, proc: ssh_command(ip, f"ps -ef | grep {proc}")),
        (r'^#ping (\d+\.\d+\.\d+\.\d+)$', lambda ip: analyze_ping_with_ai(run_ping(ip))),
        (r'^#log (\d+\.\d+\.\d+\.\d+)$', lambda ip: analyze_logs_with_ai(fetch_logs(ip))),
        (r'^#uptime (\d+\.\d+\.\d+\.\d+)$', lambda ip: analyze_uptime_with_ai(ssh_command(ip, 'uptime'))),
        (r'^#disk (\d+\.\d+\.\d+\.\d+)$', lambda ip: analyze_disk_with_ai(ssh_command(ip, 'df -h'))),
        (r'^#ps (\d+\.\d+\.\d+\.\d+) (.+)$', lambda ip, proc: analyze_ps_with_ai(ssh_command(ip, f'ps -ef | grep {proc}'))),
        (r'^!help$', lambda: (
            "🛠 사용 가능한 명령어 목록 (원문 출력):\n"
            "!ping <IP> → ping <IP>\n"
            "!log <IP> → tail -n 50 /var/log/messages\n"
            "!uptime <IP> → uptime\n"
            "!disk <IP> → df -h\n"
            "!ps <IP> <검색어> → ps -ef | grep <검색어>"
        )),
        (r'^#help$', lambda: (
            "🤖 AI 해석 포함 명령어 목록:\n"
            "#ping <IP> → ping 결과에 대한 네트워크 상태 요약\n"
            "#log <IP> → 로그 내 오류/경고 요약\n"
            "#uptime <IP> → 시스템 부하 및 가동 시간 요약\n"
            "#disk <IP> → 디스크 사용량 요약 및 위험 판별\n"
            "#ps <IP> <검색어> → 프로세스 상태 해석"
        ))
    ]

    # 패턴 매칭
    for pattern, handler in command_patterns:
        match = re.match(pattern, user_input.strip())
        if match:
            try:
                result = handler(*match.groups()) if match.groups() else handler()
                chat_logs.append({"role": "assistant", "content": result, "timestamp": timestamp})
                return jsonify({"reply": result})
            except Exception as e:
                error_msg = f"명령 처리 실패: {str(e)}"
                chat_logs.append({"role": "assistant", "content": error_msg, "timestamp": timestamp})
                return jsonify({"reply": error_msg})

    # 정의되지 않은 ! 또는 # 명령어 처리
    if user_input.strip().startswith('!') or user_input.strip().startswith('#'):
        reply = "❌ 지원하지 않는 명령어입니다. 해당 명령어에 대한 권한이 없거나 사용할 수 없습니다."
        chat_logs.append({"role": "assistant", "content": reply, "timestamp": timestamp})
        return jsonify({"reply": reply})

    # 모든 FAQ를 system prompt에 포함_NEW
    faq_reference = "\n\n".join(
        [f"[{entry['title']}] ({entry['date']})\n{entry['solution']}" for entry in FAQ_DATA.get("entries", [])]
    )
    system_prompt = "당신은 Swing AI 챗봇입니다."
    if faq_reference:
        system_prompt += (
            "\n\n다음은 우리팀이 정리해놓은 과거 인프라 장애 사례와 해결 방법입니다. "
            "GPT의 응답을 생성할 때 이 사례들을 적극 참고해 주고, 원문도 보여주세요.:\n"
            f"{faq_reference}"
        )
    try:
        print("🔍 GPT 호출 시작 >>>")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": msg["role"], "content": msg["content"]} for msg in chat_logs]
            ]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"❌ GPT 호출 실패: {str(e)}"

    chat_logs.append({"role": "assistant", "content": reply, "timestamp": timestamp})
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)

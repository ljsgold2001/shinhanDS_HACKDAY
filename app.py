from flask import Flask, render_template, request, redirect, session, jsonify
import os
import re
import paramiko
from datetime import datetime
import platform

from dotenv import load_dotenv
load_dotenv()  # ← .env 파일 로딩
#test
print("✅ SSH_USERNAME:", os.getenv("SSH_USERNAME"))
print("✅ SSH_PASSWORD:", os.getenv("SSH_PASSWORD"))

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # ← 환경변수에서 불러오기

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # ← 환경변수에서 불러오기

USER_DB = {
    "21071009": {
        "password": "123456",
        "company": "신한DS",
        "name": "고정훈"
    }
}

# SSH 자격증명도 환경변수에서 불러오기
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
# 메시지 로그 저장용
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

def run_ping(ip):
    import subprocess
    try:
        count_flag = "-n" if platform.system().lower() == "windows" else "-c"
        output = subprocess.check_output(["ping", count_flag, "1", ip], universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"Ping 실패: 응답 없음 또는 목적지에 도달하지 못했습니다.\n{e.output}"
    except Exception as e:
        return f"Ping 실패: {str(e)}"

def fetch_logs(ip):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD, timeout=5)
        stdin, stdout, stderr = ssh.exec_command("tail -n 50 /var/log/messages")
        output = stdout.read().decode()
        ssh.close()
        return output
    except Exception as e:
        return f"로그 조회 실패: {str(e)}"

def analyze_logs_with_ai(log_text):
    lines = log_text.strip().split("\n")
    key_lines = [line for line in lines if any(keyword in line.lower() for keyword in ["error", "fail", "warn", "denied", "retri", "timeout"])]
    summary = "\n".join(key_lines[:5] if key_lines else lines[:3])

    prompt = f"""
다음은 리눅스 시스템의 /var/log/messages 로그입니다. 이 로그에서 에러나 경고, 문제의 원인으로 보이는 내용을 요약해서 설명해 주세요. 한국어로 간단하게 줄바꿈해서 표현해 주세요:
# git test
{summary}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 인프라 운영 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def ssh_command(ip, command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=SSH_USERNAME, password=SSH_PASSWORD, timeout=5)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        ssh.close()
        return output
    except Exception as e:
        return f"명령어 실행 실패: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat_api():
    user_input = request.json.get("message")
    timestamp = datetime.now().strftime("%p %I:%M")
    chat_logs.append({"role": "user", "content": user_input, "timestamp": timestamp})

    if match := re.match(r'^!ping (\d+\.\d+\.\d+\.\d+)$', user_input.strip()):
        ip = match.group(1)
        result = run_ping(ip)
        chat_logs.append({"role": "assistant", "content": result, "timestamp": timestamp})
        return jsonify({"reply": result})

    elif match := re.match(r'^!log (\d+\.\d+\.\d+\.\d+)$', user_input.strip()):
        ip = match.group(1)
        logs = fetch_logs(ip)
        if "로그 조회 실패" in logs:
            chat_logs.append({"role": "assistant", "content": logs, "timestamp": timestamp})
            return jsonify({"reply": logs})
        analysis = analyze_logs_with_ai(logs)
        reply = f"📄 주요 로그:\n{logs.splitlines()[0]}\n{logs.splitlines()[1]}\n{logs.splitlines()[2]}\n\n🧠 분석:\n{analysis}"
        chat_logs.append({"role": "assistant", "content": reply, "timestamp": timestamp})
        return jsonify({"reply": reply})

    elif match := re.match(r'^!log-detail (\d+\.\d+\.\d+\.\d+)$', user_input.strip()):
        ip = match.group(1)
        logs = fetch_logs(ip)
        if "로그 조회 실패" in logs:
            chat_logs.append({"role": "assistant", "content": logs, "timestamp": timestamp})
            return jsonify({"reply": logs})
        filtered = "\n".join([line for line in logs.splitlines() if any(keyword in line.lower() for keyword in ["error", "fail", "warn", "denied", "retri", "timeout"])] or logs.splitlines()[:3])
        chat_logs.append({"role": "assistant", "content": f"📄 필터링 로그:\n{filtered}", "timestamp": timestamp})
        return jsonify({"reply": f"📄 필터링 로그:\n{filtered}"})

    elif match := re.match(r'^!uptime (\d+\.\d+\.\d+\.\d+)$', user_input.strip()):
        ip = match.group(1)
        result = ssh_command(ip, "uptime")
        chat_logs.append({"role": "assistant", "content": result, "timestamp": timestamp})
        return jsonify({"reply": result})

    elif match := re.match(r'^!disk (\d+\.\d+\.\d+\.\d+)$', user_input.strip()):
        ip = match.group(1)
        result = ssh_command(ip, "df -h")
        chat_logs.append({"role": "assistant", "content": result, "timestamp": timestamp})
        return jsonify({"reply": result})

    elif match := re.match(r'^!ps (\d+\.\d+\.\d+\.\d+) (.+)$', user_input.strip()):
        ip, proc = match.groups()
        result = ssh_command(ip, f"ps -ef | grep {proc}")
        chat_logs.append({"role": "assistant", "content": result, "timestamp": timestamp})
        return jsonify({"reply": result})

    try:
        print("🔍 GPT 호출 시작 >>>")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 Swing AI 챗봇입니다."},
                *[
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in chat_logs
                ]
            ]
        )

        print("✅ GPT 응답 완료:", response)
        reply = response.choices[0].message.content

    except Exception as e:
        reply = f"❌ GPT 호출 실패: {str(e)}"

    chat_logs.append({"role": "assistant", "content": reply, "timestamp": timestamp})
    return jsonify({"reply": reply})
if __name__ == "__main__":
    app.run(debug=True)
#test
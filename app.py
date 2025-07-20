import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# .env 파일에서 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Flask 앱 생성
app = Flask(__name__)

# CORS 설정: 프론트엔드(localhost:5173)의 /api/ 로 시작하는 모든 요청을 허용
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


# 챗봇 응답을 처리할 API 엔드포인트
@app.route("/api/chat", methods=["POST"])
def chat_with_openai():
    # 프론트엔드에서 보낸 JSON 데이터 받기
    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        # OpenAI API 호출
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
        )
        # 챗봇의 답변을 JSON 형태로 반환
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        # 오류 발생 시 에러 메시지 반환
        return jsonify({"error": str(e)}), 500
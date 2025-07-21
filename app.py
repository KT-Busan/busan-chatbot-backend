import os
from flask import Flask, request, jsonify
# from flask_cors import CORS  <- 이제 사용하지 않으므로 주석 처리하거나 삭제합니다.
from dotenv import load_dotenv
import openai

load_dotenv()

app = Flask(__name__)

# CORS(app) <- 이제 사용하지 않으므로 주석 처리하거나 삭제합니다.

# ==========================================================
# ▼▼▼▼▼ 모든 응답에 CORS 헤더를 수동으로 추가하는 부분 ▼▼▼▼▼
@app.after_request
def after_request(response):
    # 허용할 출처(프론트엔드 주소)를 명시합니다.
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    # 허용할 헤더 목록을 명시합니다.
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    # 허용할 HTTP 메소드를 명시합니다.
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
# ==========================================================

try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    client = None


# 사전 요청(OPTIONS)을 처리할 수 있도록 라우트 수정
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat_with_openai():
    # 브라우저가 보내는 사전 요청(OPTIONS)에 대해 정상 응답을 보내줍니다.
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    if not client:
        return jsonify({"error": "OpenAI API 키가 설정되지 않았거나 유효하지 않습니다."}), 500

    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "메시지가 필요합니다."}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 부산시의 청년 지원 정책과 일자리 정보를 전문적으로 알려주는 친절한 챗봇이야. 이름은 '부산 청년 지원 전문가'야. 항상 부산시의 청년 입장에서, 정확한 정보를 바탕으로 답변해줘."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response.choices[0].message.content
        return jsonify({"reply": bot_reply})
    except Exception as e:
        print(f"OpenAI API 오류: {e}")
        return jsonify({"error": "죄송합니다, 답변을 생성하는 중에 오류가 발생했습니다."}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
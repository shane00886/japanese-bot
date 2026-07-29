"""日语学习机器人 — FastAPI 主应用"""

import os
import re
import sys
import json
import random
import hashlib
import asyncio
from datetime import date, datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.core.dingtalk import webhook_bot
from app.models.database import init_db
from app.services.lesson_service import (
    init_course_data, get_user_progress, get_daily_review_words,
    record_practice, record_checkin
)
from app.templates.messages import (
    morning_teaser, lesson_card, shinchan_vocab_card
)
from app.templates.course_data import N5_LESSONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化"""
    import pathlib
    pathlib.Path("data").mkdir(exist_ok=True)
    init_db()
    init_course_data()
    print(f"🤖 {settings.BOT_NAME} ready!")
    yield
    print("🤖 Shutting down...")


app = FastAPI(title=settings.BOT_NAME, lifespan=lifespan)

# 静态文件
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ═══════════════════════════════════════════
# 页面路由
# ═══════════════════════════════════════════

@app.get("/")
@app.get("/learn")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/speech-test")
def speech_test():
    return FileResponse(os.path.join(STATIC_DIR, "speech-test.html"))


@app.get("/health")
def health():
    return {"status": "alive", "time": datetime.now().isoformat()}


# ═══════════════════════════════════════════
# TTS 语音合成 API（Google TTS）
# ═══════════════════════════════════════════

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


@app.get("/api/tts")
async def api_tts(text: str = "こんにちは", voice: str = "normal"):
    """使用 Google TTS 生成日语语音 MP3"""
    file_id = hashlib.md5(text.encode()).hexdigest()
    file_path = os.path.join(AUDIO_DIR, f"{file_id}.mp3")

    if not os.path.exists(file_path):
        try:
            from gtts import gTTS
            tts = gTTS(text, lang="ja", slow=False)
            tts.save(file_path)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return FileResponse(file_path, media_type="audio/mpeg")


# ═══════════════════════════════════════════
# 钉钉回调入口（接收群@消息）
# ═══════════════════════════════════════════

def _send_dingtalk_reply(session_webhook: str, title: str, text: str, conversation_type: str = "2", sender_id: str = ""):
    """通过钉钉回调的 sessionWebhook 发送回复"""
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }

    # 优先用 sessionWebhook（直接发送，钉钉官方推荐）
    if session_webhook:
        try:
            import requests
            r = requests.post(session_webhook, json=payload, timeout=10)
            if r.ok and r.json().get("errcode") == 0:
                return
        except Exception as e:
            print(f"sessionWebhook 失败: {e}")

    # 退回到自定义机器人 Webhook（不影响体验）
    webhook_bot.send_markdown(title, text)


@app.post("/webhook")
@app.post("/callback")
async def dingtalk_callback(request: Request):
    """
    钉钉消息回调入口
    """
    if request.method == "GET":
        return {"msg": "ok"}

    body = await request.json()

    # 把收到的消息存到日志（调试用）
    from app.models.database import get_connection
    import time
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_log (user_id, message, response, intent, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(body)[:200], json.dumps(body, ensure_ascii=False)[:2000], '', 'debug', datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"日志错误: {e}")

    # URL 验证请求
    if body.get("msg") == "ping":
        return {"msg": "pong"}

    # 处理加密/非加密的消息回调
    try:
        # 加密消息
        if "encrypt" in body:
            print(f"⚠️ 收到加密消息（需要配置加解密密钥）")
            # 尝试用默认 Token/AES 解密（DingTalk 默认密钥需要从后台获取）
            # 暂时返回成功，让钉钉知道我们收到了
            return {"msg": "success", "error": "encrypted - need AES config"}

        sender_id = body.get("senderId") or body.get("senderStaffId", "") or "unknown"
        session_webhook = body.get("sessionWebhook", "") or body.get("webhook", "")
        conversation_type = body.get("conversationType", "1")  # 1=单聊 2=群聊

        # 提取文本
        text = ""
        msg_body = body.get("text", {})
        if isinstance(msg_body, dict):
            text = msg_body.get("content", "")
        elif isinstance(msg_body, str):
            text = msg_body

        # 语音消息（钉钉自动转文字）
        if not text and body.get("msgtype") == "voice":
            text = body.get("recognition", "")
            print(f"🎤 语音识别: {text}")

        # 如果还没提取到文字，检查其他常见字段
        if not text:
            text = body.get("text", "") or body.get("content", "") or ""

        text = re.sub(r'@[^\s]+', '', text).strip().strip('"\' \t\n')

        if not text:
            return {"msg": "success"}

        # 处理并回复
        reply = handle_message(sender_id, text, conversation_type)
        _send_dingtalk_reply(session_webhook, "日本语先生", reply, conversation_type, sender_id)

    except Exception as e:
        print(f"❌ 处理错误: {e}")
        import traceback
        traceback.print_exc()

    return {"msg": "success"}


# 调试接口 - 查看最近收到的回调
@app.get("/debug/logs")
def debug_logs(limit: int = 10):
    """查看最近的回调日志"""
    from app.models.database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM chat_log WHERE intent='debug' ORDER BY id DESC LIMIT ?", (limit,))
    logs = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"logs": logs, "count": len(logs)}


# 同时支持 GET 请求（钉钉会发送 GET 来验证）
@app.get("/webhook")
@app.get("/callback")
def dingtalk_get_callback():
    """钉钉 GET 验证"""
    return {"msg": "ok"}


# ═══════════════════════════════════════════
# 消息处理
# ═══════════════════════════════════════════

def handle_message(user_id: str, text: str, conversation_type: str = "1") -> str:
    """使用 AI 日语老师处理所有消息"""
    from app.services.teacher import process_message
    return process_message(user_id, text)


# 以下函数保留用于旧版兼容，新逻辑都在 teacher.py 中
def _do_checkin(user_id: str) -> str:
    from app.services.lesson_service import record_checkin, get_user_progress
    record_checkin(user_id)
    p = get_user_progress(user_id)
    return f"✅ 打卡成功！连续 {p['streak_days']} 天 🔥\n💎 经验值 +25（累计 {p['xp']}）"

def _do_status(user_id: str) -> str:
    from app.services.lesson_service import get_user_progress, get_level_emoji
    p = get_user_progress(user_id)
    lesson = p.get("current_lesson")
    title = lesson["title"] if lesson else "全部完成！"
    emoji = get_level_emoji(p["level"])
    return f"📊 {p['level']} {emoji} | 💎{p['xp']} | 🔥{p['streak_days']}天 | 📖{title}"

def _do_mission(user_id: str) -> str:
    from app.services.lesson_service import get_user_progress
    p = get_user_progress(user_id)
    lesson = p.get("current_lesson")
    if not lesson:
        return "🎉 全部完成！"
    return f"📖 今日任务：{lesson['title']}\n去 H5 页面学习吧！\nhttps://japanese-bot-g5pq.onrender.com/learn"


# ═══════════════════════════════════════════
# API 接口（给 H5 页面调用的后端 API）
# ═══════════════════════════════════════════

@app.get("/api/user/{user_id}")
def api_get_user(user_id: str):
    """获取用户数据"""
    p = get_user_progress(user_id)
    return {
        "level": p["level"],
        "xp": p["xp"],
        "streak_days": p["streak_days"],
        "max_streak": p["max_streak"],
        "current_lesson": {
            "id": p["current_lesson"]["lesson_id"] if p["current_lesson"] else None,
            "title": p["current_lesson"]["title"] if p["current_lesson"] else None,
        },
        "completed": p["completed_lessons"],
        "progress_pct": p["progress_pct"],
    }


@app.get("/api/lessons")
def api_get_lessons():
    """获取所有课程"""
    lessons = []
    for l in N5_LESSONS:
        lessons.append({
            "id": l["lesson_id"],
            "no": l["lesson_no"],
            "title": l["title"],
            "chapter": l["chapter"],
            "desc": l["description"],
            "vocab_count": l["vocab_count"],
        })
    return {"lessons": lessons}


@app.post("/api/checkin/{user_id}")
def api_checkin(user_id: str):
    """打卡"""
    record_checkin(user_id)
    p = get_user_progress(user_id)
    return {"ok": True, "streak": p["streak_days"], "xp": p["xp"]}


@app.post("/api/test/send")
def api_test_send():
    """测试发送消息到钉钉群"""
    result = webhook_bot.send_markdown(
        "🧪 测试消息",
        "### 🧪 测试消息\n\n机器人测试成功！\n\n> H5 页面：https://japanese-bot-g5pq.onrender.com/learn"
    )
    return {"sent": result.get("errcode") == 0, "detail": result}

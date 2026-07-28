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

@app.post("/webhook")
@app.post("/callback")
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
    """处理用户消息，返回中文回复"""
    text = text.strip().lower()

    # 打卡
    if any(kw in text for kw in ["打卡", "签到", "完成"]):
        return _do_checkin(user_id)

    # 进度查询
    if any(kw in text for kw in ["进度", "成绩", "等级", "经验", "多少"]):
        return _do_status(user_id)

    # 今日任务
    if any(kw in text for kw in ["任务", "今天", "闯关", "开始"]):
        return _do_mission(user_id)

    # 复习
    if any(kw in text for kw in ["复习", "回顾"]):
        return _do_review(user_id)

    # 帮助
    if any(kw in text for kw in ["帮助", "help", "命令", "怎么用"]):
        return _help_text()

    # 查询单词
    if any(kw in text for kw in ["怎么说", "什么意思", "翻译"]):
        return _do_translate(text)

    # 小新相关
    if any(kw in text for kw in ["小新", "新之助", "蜡笔小新", "しんちゃん"]):
        return _shinchan_fact()

    # 跳转到学习页面
    if any(kw in text for kw in ["页面", "网页", "h5", "学习"]):
        return f"📚 点这里开始学习：\nhttps://japanese-bot-g5pq.onrender.com/learn"

    # 兜底
    return _fallback()


def _do_checkin(user_id: str) -> str:
    """打卡"""
    try:
        record_checkin(user_id)
        p = get_user_progress(user_id)
        s = p["streak_days"]
        xp = p["xp"]

        if s == 1:
            return f"🎉 打卡成功！第一天开始啦！🔥\n💎 经验值 +25（累计 {xp}）\n\n「好的开始是成功的一半！」"
        if s == 7:
            return f"🎊 连续 7 天！太厉害了！🔥🔥🔥\n💎 经验值 +25（累计 {xp}）\n\n「你已经超越大多数人了！」"
        if s == 30:
            return f"👑👑👑 连续 30 天！传奇达成！\n💎 经验值 +25（累计 {xp}）\n\n「你已经是日语达人了！」"

        msg = f"✅ 打卡成功！连续 {s} 天 🔥\n💎 经验值 +25（累计 {xp}）"
        if s in [3, 5, 10, 14, 21]:
            msg += f"\n🎖️ 解锁成就：连续 {s} 天！"
        return msg
    except Exception as e:
        return f"❌ 打卡失败：{e}"


def _do_status(user_id: str) -> str:
    """查询进度"""
    try:
        p = get_user_progress(user_id)
        lesson = p["current_lesson"]
        title = lesson["title"] if lesson else "全部完成！"
        return (
            f"📊 **学习报告**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎖️ 等级：{p['level']}\n"
            f"💎 经验值：{p['xp']}\n"
            f"🔥 连续学习：{p['streak_days']} 天\n"
            f"🏆 最长记录：{p['max_streak']} 天\n"
            f"📖 当前课程：{title}\n"
            f"📈 总进度：{p['progress_pct']}%（{p['completed_lessons']}/{p['total_lessons']} 章）\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"继续加油！🎯"
        )
    except Exception as e:
        return f"❌ 查询失败：{e}"


def _do_mission(user_id: str) -> str:
    """今日任务"""
    try:
        p = get_user_progress(user_id)
        lesson = p.get("current_lesson")
        if not lesson:
            return "🎉 所有课程都学完啦！等着我出新课吧！"

        # 获取单词
        from app.models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vocabulary WHERE lesson_id = ?", (lesson["lesson_id"],))
        vocab = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # 发送课程卡片
        card = lesson_card(
            lesson_title=lesson["title"],
            shinchan_line=lesson.get("shinchan_line", ""),
            vocab_list=vocab,
            grammar=lesson["grammar_points"],
        )
        webhook_bot.send_markdown(f"📖 {lesson['title']}", card)

        return (
            f"🔥 今天的任务是「{lesson['title']}」！\n"
            f"📝 学习 {len(vocab)} 个新单词\n"
            f"⏱ 大约需要 12 分钟\n\n"
            f"学完后说「打卡」来记录哦！"
        )
    except Exception as e:
        return f"❌ 获取任务失败：{e}"


def _do_review(user_id: str) -> str:
    """复习旧词"""
    try:
        words = get_daily_review_words(user_id)
        if not words:
            return "📚 今天没有需要复习的单词！学新词的时候我会提醒你的。"

        lines = "\n".join([
            f"  🔄 **{w['japanese']}**（{w['kana']}）— {w['meaning']}"
            for w in words
        ])
        return f"🔄 **今天要复习 {len(words)} 个词：**\n\n{lines}\n\n「记不住的词要多看几遍哦！」"
    except Exception as e:
        return f"❌ 获取复习词失败：{e}"


def _do_translate(text: str) -> str:
    """简单翻译"""
    try:
        q = text
        for kw in ["怎么说", "什么意思", "翻译", "日语"]:
            q = q.replace(kw, "")
        q = q.strip()

        if not q:
            return "💡 试试这样问我：\n「苹果 怎么说」\n「ラーメン 什么意思」"

        from app.models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT japanese, kana, meaning FROM vocabulary WHERE japanese LIKE ? LIMIT 1",
            (f"%{q}%",)
        )
        w = cursor.fetchone()
        if w:
            conn.close()
            return f"🔤 {w['japanese']}（{w['kana']}）\n→ {w['meaning']}"

        cursor.execute(
            "SELECT japanese, kana, meaning FROM vocabulary WHERE meaning LIKE ? LIMIT 1",
            (f"%{q}%",)
        )
        w = cursor.fetchone()
        conn.close()
        if w:
            return f"🔤 {q} → {w['japanese']}（{w['kana']}）"

        return f"「{q}」还没学到呢！学新词的时候我教你！📖"
    except Exception as e:
        return f"❌ 查询出错：{e}"


def _shinchan_fact() -> str:
    """小新冷知识"""
    facts = [
        ("🎬 **蜡笔小新冷知识**\n\n小新全名叫「野原新之助」，今年 5 岁！最爱吃巧克力饼干和咖喱饭！"),
        ("🎬 **蜡笔小新冷知识**\n\n小新常说的「オラ」是日本关东地区的小孩用语。大人一般说「ぼく」或「わたし」。"),
        ("🎬 **蜡笔小新冷知识**\n\n小新的妹妹叫「野原向日葵」，名字的意思是像向日葵一样阳光地成长！"),
        ("🎬 **蜡笔小新冷知识**\n\n小新住在埼玉县春日部市，蜡笔小新的故事就发生在这里！"),
        ("🎬 **蜡笔小新名言**\n\n「开心的事最重要！学习也要开开心心地学！」"),
        ("🎬 **蜡笔小新名言**\n\n小新最经典的口头禅之一：「美女，一起吃个饭怎么样？」😂"),
    ]
    return random.choice(facts)[0]


def _help_text() -> str:
    return (
        "📋 **小新日语助手 使用说明**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📖 **「任务」** — 查看今天的学习内容\n"
        "✅ **「打卡」** — 学完了，记录一下\n"
        "📊 **「进度」** — 看看自己的学习情况\n"
        "🔄 **「复习」** — 复习以前学过的单词\n"
        "🔤 **「XX 怎么说」** — 查单词的中文→日文\n"
        "🔤 **「XX 什么意思」** — 查单词的日文→中文\n"
        "🎬 **「小新」** — 看看蜡笔小新的冷知识\n"
        "📚 **「学习」** — 打开 H5 学习页面\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "直接在群里问我吧！💪"
    )


def _fallback() -> str:
    replies = [
        "🤔 不明白你在说什么……试试说「任务」或「帮助」吧！",
        "😅 我还不太懂这个……你可以说「帮助」看看我会什么！",
        "💪 继续加油！不懂的就说「帮助」，我教你！",
        "🎯 说「任务」开始今天的学习，说「打卡」记录完成！",
        "📖 不知道怎么用？说「帮助」看看使用说明！",
    ]
    return random.choice(replies)


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

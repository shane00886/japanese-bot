"""日语学习机器人 — FastAPI 主应用"""

import os
import json
import random
from datetime import date, datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.dingtalk import DingTalkClient, ding_client
from app.models.database import init_db
from app.services.lesson_service import (
    init_course_data, get_user_progress, get_daily_review_words,
    record_practice, record_checkin
)
from app.templates.messages import (
    morning_teaser, lesson_card, mission_complete,
    status_report, shinchan_quote_random, shinchan_vocab_card
)
from app.templates.course_data import N5_LESSONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化"""
    print(f"🤖 {settings.BOT_NAME} starting up...")
    init_db()
    init_course_data()
    yield
    print("🤖 Shutting down...")


app = FastAPI(title=settings.BOT_NAME, lifespan=lifespan)

# 挂载静态文件（H5 学习页面）
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ─── 页面路由 ───

@app.get("/")
@app.get("/learn")
def root():
    """H5 学习页面"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "alive", "time": datetime.now().isoformat()}


# ─── 钉钉消息回调（接收 @机器人的消息） ───

@app.post("/webhook")
async def webhook(request: Request):
    """钉钉消息回调入口"""
    body = await request.json()
    print(f"📩 收到消息: {json.dumps(body, ensure_ascii=False)[:200]}")

    # 解析钉钉回调消息
    try:
        sender_id = body.get("senderId") or body.get("senderStaffId", "")
        conversation_type = body.get("conversationType", "")
        conversation_id = body.get("conversationId", "")
        text = ""
        msg_body = body.get("text", {}) or body.get("content", {})
        if isinstance(msg_body, dict):
            text = msg_body.get("content", "")
        elif isinstance(msg_body, str):
            text = msg_body

        # 去掉 @机器人的部分
        import re
        text = re.sub(r'@[^\s]+', '', text).strip()

        if not text:
            return {"msg": "ok"}

        # 处理消息
        reply = await handle_message(sender_id, text, conversation_id)

        # 如果是群聊，通过机器人发消息回复
        if conversation_type == "group":
            ding_client.send_group_markdown(
                conversation_id, "しんちゃん先生", reply
            )
        else:
            ding_client.send_markdown_message(
                sender_id, "しんちゃん先生", reply
            )

    except Exception as e:
        print(f"❌ 消息处理错误: {e}")

    return {"msg": "ok"}


async def handle_message(user_id: str, text: str, conversation_id: str) -> str:
    """处理用户消息，返回回复文本"""
    text = text.strip().lower()

    # ── 功能触发类 ──
    if any(kw in text for kw in ["打卡", "checkin", "完成"]):
        return await do_checkin(user_id)

    if any(kw in text for kw in ["进度", "status", "成绩", "多少级", "xp", "经验"]):
        return await do_status(user_id)

    if any(kw in text for kw in ["任务", "今天", "开始", "mission", "闯关"]):
        return await do_daily_mission(user_id, conversation_id)

    if any(kw in text for kw in ["复习", "review", "复習"]):
        return await do_review(user_id)

    if any(kw in text for kw in ["帮助", "help", "用法", "命令"]):
        return get_help_text()

    # ── 单词查询 ──
    if any(kw in text for kw in ["怎么说", "什么意思", "意思是", "日语", "翻译"]):
        return await do_translate(text)

    # ── 闲聊／しんちゃん ──
    if any(kw in text for kw in ["しんちゃん", "新之助", "小新", "蜡笔小新"]):
        return get_shinchan_fun_fact()

    return get_fallback_text()


# ── 各功能实现 ──

async def do_checkin(user_id: str) -> str:
    try:
        record_checkin(user_id)
        progress = get_user_progress(user_id)
        streak = progress["streak_days"]
        xp = progress["xp"]
        level = progress["level"]

        # 彩蛋
        if streak == 7:
            return f"🎊 **7日連続達成！**🔥\n\nよくやった！もうアクション仮面級のヒーローだ！\n💎 XP +25（累計 {xp}）\n🎖️ {level}\n\n「オラも見習わないと！明日も待ってるゾ！」"
        elif streak == 30:
            return f"🎊🎊 **30日連続！レジェンド達成！** 🎊🎊\n\n野原家の誇りだゾ！これからもがんばれ！\n💎 XP +25（累計 {xp}）\n🎖️ {level}"

        return f"🎊 **チェックイン完了！**\n🔥 連続学習：{streak} 日目\n💎 XP +25（累計 {xp} XP）\n🎖️ {level}\n\n「継続は力なり！明日も来いよ！」"
    except Exception as e:
        return f"❌ 打卡失败了：{e}"


async def do_status(user_id: str) -> str:
    progress = get_user_progress(user_id)
    return status_report(
        xp=progress["xp"],
        level=progress["level"],
        streak=progress["streak_days"],
        max_streak=progress["max_streak"],
        current_lesson=progress["current_lesson"]["title"] if progress["current_lesson"] else "全部完了！",
        progress_pct=progress["progress_pct"],
    )


async def do_daily_mission(user_id: str, conversation_id: str) -> str:
    """准备每日任务"""
    progress = get_user_progress(user_id)
    lesson = progress.get("current_lesson")

    if not lesson:
        return "🎉 **全部の課程を修了しました！** おめでとう！\n\n新しいコンテンツをお待ちください！"

    # 获取课程词汇
    from app.models.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vocabulary WHERE lesson_id = ?", (lesson["lesson_id"],))
    vocab_list = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # 发送学习卡片
    card = lesson_card(
        lesson_title=lesson["title"],
        shinchan_line=lesson.get("shinchan_line", ""),
        vocab_list=vocab_list,
        grammar=lesson["grammar_points"],
    )
    # 由于是���步回复，直接发送到群里
    ding_client.send_group_markdown(conversation_id, f"📖 {lesson['title']}", card)

    vocab_card = shinchan_vocab_card(vocab_list)
    ding_client.send_group_markdown(conversation_id, "📺 しんちゃんの単語帳", vocab_card)

    return f"🔥 今日は「{lesson['title']}」の修行だ！上のカードを見て勉強してね！\n覚えたら「打卡」って言って教えて！"


async def do_review(user_id: str) -> str:
    words = get_daily_review_words(user_id)
    if not words:
        return "📚 **今日の復習はありません！**\n新しい単語を覚えて、明日またチェックしよう！"

    lines = "\n".join([
        f"  🔄 **{w['japanese']}**（{w['kana']}）— {w['meaning']}"
        f"\n    📝 {w['example']}"
        for w in words
    ])
    return f"🔄 **復習タイム！**\n\n今日は {len(words)} 語の復習だ！\n\n{lines}\n\n「忘れる前に復習するのが大事だゾ！」"


async def do_translate(text: str) -> str:
    """简单翻译/单词查询（基于已有词库）"""
    from app.models.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()

    # 提取可能的查询词
    query_word = text.replace("怎么说", "").replace("什么意思", "").replace("日语", "").replace("翻译", "").replace(" ", "").strip()

    # 查日→中
    cursor.execute(
        "SELECT japanese, kana, meaning, example, example_meaning FROM vocabulary WHERE japanese LIKE ? LIMIT 1",
        (f"%{query_word}%",)
    )
    word = cursor.fetchone()

    if word:
        return f"🔤 **{word['japanese']}**（{word['kana']}）\n→ {word['meaning']}\n📝 {word['example']}（{word['example_meaning']}）"

    # 查中→日
    cursor.execute(
        "SELECT japanese, kana, meaning FROM vocabulary WHERE meaning LIKE ? LIMIT 1",
        (f"%{query_word}%",)
    )
    word = cursor.fetchone()
    conn.close()

    if word:
        return f"🔤 {query_word} → **{word['japanese']}**（{word['kana']}）"

    return f"「{query_word}」は…まだ習ってないゾ！新しい単語を勉強したらまた聞いてくれ！"


def get_shinchan_fun_fact() -> str:
    facts = [
        "🎬 **しんちゃん豆知識**\n\nしんちゃんの本名は「野原しんのすけ」。年齢は5歳！好きな食べ物はチョコビとカレー！",
        "🎬 **しんちゃん豆知識**\n\nしんちゃんの口ぐせ「オラ」は、実は関東地方の子供言葉。大人の男性は「ぼく」、女性は「わたし」を使うんだゾ！",
        "🎬 **しんちゃん豆知識**\n\nしんちゃんの妹「ひまわり」の名前の由来は、太陽に向かって咲くヒマワリのように元気に育ってほしいから！",
        "🎬 **しんちゃん豆知識**\n\nしんちゃんが住んでいるのは埼玉県春日部市！「クレヨンしんちゃん」の舞台なんだゾ！",
        "🎬 **しんちゃんの名言**\n\n「楽しいことが一番だゾ！勉強も楽しんでやるのがコツ！」",
    ]
    return random.choice(facts)


def get_fallback_text() -> str:
    """兜底回复"""
    replies = [
        "うーん…難しい質問だ！修行中の身にはまだ早すぎるゾ！また後で聞いてくれ！",
        "ごめん！まだその質問に答えられないんだ。もっと勉強してから戻ってくる！",
        "おっ！いい質問だ！でも今はまだ修行中でな…許してくれ！",
        "その質問、師匠に聞いてみないとわからないゾ！また明日な！",
        "ブッブー！その質問にはまだ答えられないゾ！でも気にするな！",
    ]
    return random.choice(replies)


def get_help_text() -> str:
    return """
📋 **しんちゃん先生　使い方**

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔹 **今日のタスク**
  「任务」「今天」「闯关」
  → 今日の学習内容を表示

🔹 **チェックイン**
  「打卡」「checkin」
  → 学習完了を記録

🔹 **進捗確認**
  「进度」「status」「经验」
  → 現在の学習状況を表示

🔹 **単語クエリ**
  「XX 怎么说」「XX 什么意思」
  → 単語の意味を調べる

🔹 **復習**
  「复习」「review」
  → 今日の復習単語を表示

🔹 **しんちゃん**
  「しんちゃん」「新之助」
  → しんちゃん豆知識を表示
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """.strip()


# ─── 手动测试接口（用于第一次验证） ───

@app.post("/test/send")
async def test_send(conversation_id: str = "test"):
    """测试发送一条早安卡片"""
    if conversation_id == "test":
        return {"message": "请提供真实的 openConversationId", "help": "从钉钉群设置中获取群ID"}

    card = morning_teaser(
        lesson_title="冒険の始まり",
        chapter="开学季 · 自我介绍",
        duration=12,
        xp=25,
    )
    result = ding_client.send_group_markdown(conversation_id, "🌅 おはよう！", card)
    return {"sent": True, "result": result}


@app.post("/test/lesson")
async def test_lesson(conversation_id: str = "test"):
    """测试发送课程卡片"""
    if conversation_id == "test":
        return {"message": "请提供真实的 openConversationId"}

    lesson = N5_LESSONS[0]
    from app.models.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vocabulary WHERE lesson_id = ?", (lesson["lesson_id"],))
    vocab_list = [dict(row) for row in cursor.fetchall()]
    conn.close()

    card = lesson_card(
        lesson_title=lesson["title"],
        shinchan_line=lesson["shinchan_line"],
        vocab_list=vocab_list,
        grammar=lesson["grammar_points"],
    )
    result = ding_client.send_group_markdown(conversation_id, f"📖 {lesson['title']}", card)
    return {"sent": True, "result": result}

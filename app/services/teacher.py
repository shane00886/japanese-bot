"""
🧒 小新AI日语老师 - 互动教学引擎
支持自然对话、教学、测验、激励
"""

import re
import random
import json

# ─── 对话状态管理 ─────────────────────────────
# 每个用户的状态
_user_state: dict[str, dict] = {}

def get_state(user_id: str) -> dict:
    if user_id not in _user_state:
        _user_state[user_id] = {
            "mode": "idle",           # idle | teaching | quiz | review
            "last_word": None,        # 最近教的单词 {japanese, kana, meaning, example}
            "quiz_word": None,        # 当前考的是哪个词
            "quiz_type": None,        # jp2cn | cn2jp
            "correct_streak": 0,      # 连续答对次数
            "xp_this_session": 0,     # 本次会话获得的经验
        }
    return _user_state[user_id]


# ─── 表情辅助 ─────────────────────────────────
def xp_reward(xp: int) -> str:
    if xp >= 50: return "🎉🎉🎉"
    if xp >= 30: return "🎉🎉"
    if xp >= 15: return "⭐"
    return ""


# ─── 主处理函数 ───────────────────────────────
def process_message(user_id: str, text: str) -> str:
    """
    处理用户消息，返回回复内容
    优先使用 AI 理解，降级到关键词匹配
    """
    text = text.strip()

    # 先试 AI
    from app.services.ai_chat import ask_ai
    ai_reply = ask_ai(text, user_id)
    if ai_reply:
        return ai_reply

    # AI 不可用，走 NLP 兜底
    return _keyword_match(user_id, text)


def process_message(user_id: str, text: str) -> str:
    """新入口：使用 AI 智能对话"""
    from app.services.ai_chat import process_smart
    return process_smart(user_id, text)


def _keyword_match(user_id: str, text: str) -> str:
    """关键词匹配兜底"""
    state = get_state(user_id)

    if _match(text, ["你好", "您好", "嗨", "hi", "hello"]):
        return _greeting(user_id)
    if _match(text, ["想学", "教我", "学日语", "教日语", "开始学", "学习", "今天学", "能教我", "好的", "好啊", "行", "可以", "来吧", "开始", "上课"]):
        return _start_teaching(user_id)
    if any(kw in text for kw in ["怎么说", "什么意思", "翻译", "用日语"]):
        return _lookup_word(text)
    if _match(text, ["小新", "新之助", "蜡笔小新", "しんちゃん"]):
        return _shinchan_reply()
    if _match(text, ["考考我", "出题", "考试", "考我", "测验", "测试", "做题"]):
        return _start_quiz(user_id)
    if _match(text, ["打卡", "签到", "学完了", "完成了"]):
        from app.services.lesson_service import record_checkin, get_user_progress
        record_checkin(user_id)
        p = get_user_progress(user_id)
        return f"✅ 打卡成功！🔥 {(p.get('streak_days', 0))} 天\n💎 +25XP（累计 {p.get('xp', 0)}）"
    if _match(text, ["进度", "成绩", "等级", "经验", "我多少"]):
        from app.services.lesson_service import get_user_progress, get_level_emoji
        p = get_user_progress(user_id)
        emoji = get_level_emoji(p.get("level", "N5"))
        return f"📊 {p.get('level', 'N5')} {emoji} | 💎{p.get('xp', 0)} | 🔥{p.get('streak_days', 0)}天"
    if state["mode"] == "quiz" and state.get("quiz_word"):
        return _check_answer(user_id, text, state)
    return _fallback_reply(user_id)


# ─── 匹配函数（更自然的匹配） ──────────────────
def _match(text: str, keywords: list[str]) -> bool:
    """更智能的匹配：包含任一关键词"""
    text = text.lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False


# ─── 1. 打招呼 ──────────────────────────────
def _greeting(user_id: str) -> str:
    from app.services.lesson_service import get_user_progress
    p = get_user_progress(user_id)
    streak = p.get("streak_days", 0)

    return (
        f"🎌 **こんにちは！我是しんちゃん！**\n\n"
        f"我是你的日语小老师，今年5岁！\n"
        f"每天和我一起学日语吧！📖\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **每日任务**\n"
        f"1. 📖 打开 H5 学习 → 点这里\n"
        f"2. 🎤 跟着朗读发音\n"
        f"3. ✅ 学完告诉我「**打卡**」\n\n"
        f"📊 说「**进度**」看你的学习报告\n"
        f"🎯 说「**考考我**」我来出题\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{'🔥 你已经在坚持第 ' + str(streak) + ' 天了！' if streak > 0 else '💪 今天开始第一天吧！'}"
    )


# ─── 2. 开始教学 ─────────────────────────────
def _start_teaching(user_id: str) -> str:
    """教一个新单词"""
    from app.models.database import get_connection
    from app.services.lesson_service import get_user_progress, add_xp

    # 获取当前课程
    p = get_user_progress(user_id)
    lesson = p.get("current_lesson")

    if not lesson:
        return "🎉 所有课程都学完啦！你太厉害了！等着我出新课吧！"

    # 从当前课程随机取一个单词
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT japanese, kana, meaning, example_jp, example_cn FROM vocabulary WHERE lesson_id = ? ORDER BY RANDOM() LIMIT 1",
        (lesson["lesson_id"],)
    )
    word = cursor.fetchone()
    conn.close()

    if not word:
        return "哎呀，单词库空了……让我补充一下！"

    word = dict(word)

    # 保存教学状态
    state = get_state(user_id)
    state["mode"] = "teaching"
    state["last_word"] = word
    state["correct_streak"] = 0

    # 给参与经验
    add_xp(user_id, 3)

    # 构建回复
    example = ""
    if word.get("example_jp") and word.get("example_cn"):
        example = f"\n📝 例子：{word['example_jp']}\n       → {word['example_cn']}"

    return (
        f"📖 **新单词来啦！**\n\n"
        f"🔤 **{word['japanese']}**\n"
        f"  读作：{word['kana']}\n"
        f"  意思：{word['meaning']}"
        f"{example}\n\n"
        f"跟我读一遍！读好了告诉我哦 😊\n"
        f"也可以说「考考我」看看记住了没！"
    )


# ─── 3. 查单词 ──────────────────────────────
def _lookup_word(text: str) -> str:
    from app.models.database import get_connection
    for kw in ["怎么说", "什么意思", "翻译", "用日语", "用日语怎么说", "日语是"]:
        text = text.replace(kw, "").strip()

    if not text:
        return "💡 可以这样问我：\n「苹果 怎么说」\n「ありがとう 什么意思」"

    conn = get_connection()
    cursor = conn.cursor()

    # 先查 日→中
    cursor.execute(
        "SELECT japanese, kana, meaning FROM vocabulary WHERE japanese LIKE ? LIMIT 1",
        (f"%{text}%",)
    )
    w = cursor.fetchone()
    if w:
        conn.close()
        return (
            f"🔤 **{w['japanese']}**（{w['kana']}）\n"
            f"→ {w['meaning']}\n\n"
            f"记住了吗？😊"
        )

    # 再查 中→日
    cursor.execute(
        "SELECT japanese, kana, meaning FROM vocabulary WHERE meaning LIKE ? LIMIT 1",
        (f"%{text}%",)
    )
    w = cursor.fetchone()
    conn.close()
    if w:
        return (
            f"🔤 「{text}」的日语是：\n"
            f"**{w['japanese']}**（{w['kana']}）\n\n"
            f"跟我读！{w['japanese']} 📖"
        )

    return f"😅 「{text}」我还没学到呢！等我学了再教你！"


# ─── 4. 小新台词 ─────────────────────────────
def _shinchan_reply() -> str:
    quotes = [
        ("「オラはしんのすけ！」\n→ 我是小新！", "小新最经典的开场白！"),
        ("「おはよう、おねいさん！」\n→ 早上好，大姐姐！", "小新看到美女的口头禅 😂"),
        ("「え〜、めんどくさい！」\n→ 诶〜好麻烦！", "小新不想做作业时经常说！"),
        ("「ママ、ごはんまだ？」\n→ 妈妈，饭还没好？", "小新肚子饿的时候必说！"),
        ("「おやつは３時だよね！」\n→ 点心是3点对吧！", "小新最爱巧克力饼干 🍪"),
    ]
    quote, tip = random.choice(quotes)
    return (
        f"🎭 **しんちゃん语录**\n\n"
        f"{quote}\n\n"
        f"💡 {tip}\n\n"
        f"说「教我」继续学日语吧！"
    )


# ─── 5. 开始测验 ─────────────────────────────
def _start_quiz(user_id: str) -> str:
    """出题考用户"""
    from app.models.database import get_connection
    from app.services.lesson_service import get_user_progress

    p = get_user_progress(user_id)
    lesson = p.get("current_lesson")
    if not lesson:
        return "所有课程都学完了！没有题可以出了 🎉"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT japanese, kana, meaning FROM vocabulary WHERE lesson_id = ? ORDER BY RANDOM() LIMIT 1",
        (lesson["lesson_id"],)
    )
    word = cursor.fetchone()
    conn.close()

    if not word:
        return "题库空了……让我先学点新词！"

    word = dict(word)
    quiz_type = random.choice(["jp2cn", "cn2jp"])

    state = get_state(user_id)
    state["mode"] = "quiz"
    state["quiz_word"] = word
    state["quiz_type"] = quiz_type
    state["correct_streak"] = state.get("correct_streak", 0)

    if quiz_type == "jp2cn":
        return (
            f"🎯 **小测验！**\n\n"
            f"「{word['japanese']}」（{word['kana']}）\n"
            f"是什么意思呢？🤔\n\n"
            f"把答案发给我！"
        )
    else:
        return (
            f"🎯 **小测验！**\n\n"
            f"「{word['meaning']}」\n"
            f"用日语怎么说？🤔\n\n"
            f"把日语发给我！"
        )


# ─── 6. 检查答案 ─────────────────────────────
def _check_answer(user_id: str, answer: str, state: dict) -> str:
    """检查用户对测验的回答"""
    from app.services.lesson_service import add_xp

    word = state["quiz_word"]
    quiz_type = state["quiz_type"]
    correct_streak = state.get("correct_streak", 0)

    answer = answer.strip().lower()
    expected_jp = word["japanese"].lower().strip()
    expected_cn = word["meaning"].lower().strip()

    is_correct = False
    if quiz_type == "jp2cn":
        # 检查中文答案（部分匹配即可）
        if answer in expected_cn or expected_cn in answer:
            is_correct = True
    else:
        # 检查日语答案（部分匹配即可）
        if answer in expected_jp or expected_jp in answer:
            is_correct = True

    state["mode"] = "idle"

    if is_correct:
        correct_streak += 1
        state["correct_streak"] = correct_streak
        bonus = 0

        base_xp = 10
        if correct_streak >= 5:
            bonus = 50
            msg = f"🏆 **连续 {correct_streak} 题全对！你是天才吗？！**"
        elif correct_streak >= 3:
            bonus = 20
            msg = f"🔥 **连续 {correct_streak} 题全对！太厉害了！**"
        else:
            bonus = 0
            msg = "🎉 **答对了！**"

        total_xp = base_xp + bonus
        add_xp(user_id, total_xp)

        return (
            f"{msg}\n\n"
            f"💎 +{total_xp} 经验值！{xp_reward(total_xp)}\n\n"
            f"再说「考考我」继续挑战！\n"
            f"或者说「教我」学新词！"
        )
    else:
        # 答错了
        state["correct_streak"] = 0
        hint = f"正确答案是：**{word['japanese']}**（{word['kana']}）— {word['meaning']}"

        return (
            f"😅 再想想……\n"
            f"{hint}\n\n"
            f"没关系，记住就好！说「考考我」再来一题！"
        )


# ─── 7. 复习 ─────────────────────────────────
def _start_review(user_id: str) -> str:
    from app.services.lesson_service import get_daily_review_words
    words = get_daily_review_words(user_id)

    if not words:
        return "📚 今天没有需要复习的单词！学完新词找我复习哦！"

    lines = "\n".join([
        f"  🔄 **{w['japanese']}**（{w['kana']}）— {w['meaning']}"
        for w in words
    ])
    return (
        f"🔄 **今天要复习 {len(words)} 个词：**\n\n"
        f"{lines}\n\n"
        f"都记住了吗？说「考考我」我帮你测试一下！"
    )


# ─── 兜底回复 ─────────────────────────────────
def _fallback_reply(user_id: str) -> str:
    replies = [
        "😊 试试这样做：\n"
        "• 学完了说「**打卡**」\n"
        "• 学新词说「**教我**」\n"
        "• 考考我说「**考考我**」\n"
        "• 看进度说「**进度**」",

        "📖 **每日任务**：\n"
        "1️⃣ 打开 H5 学习：https://japanese-bot-g5pq.onrender.com/learn\n"
        "2️⃣ 学完回来说「**打卡**」🔥",

        "💪 今天打卡了吗？\n"
        "说「**打卡**」记录学习！\n"
        "说「**进度**」看成就！🎯",
    ]
    return random.choice(replies)

"""消息模板 — 所有推送给钉群的卡片文案"""


def morning_teaser(lesson_title: str, chapter: str, duration: int, xp: int) -> str:
    """早安预告卡片"""
    return f"""
🌅 **おはよう！師匠からのミッションだ！**

━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 **今日の修行メニュー**

**「{lesson_title}」** — {chapter}
⏱ 必要時間：約 {duration} 分
💎 獲得可能 XP：+{xp}

━━━━━━━━━━━━━━━━━━━━━━━━━━
放課後に一気に片付けろ！🔥
    """.strip()


def lesson_card(lesson_title: str, shinchan_line: str, vocab_list: list, grammar: str) -> str:
    """知识小课堂卡片"""
    vocab_text = "\n".join([
        f"  {v['japanese']}（{v['kana']}）— {v['meaning']}"
        for v in vocab_list
    ])
    return f"""
⚔️ **今日の任務：{lesson_title}**

📖 **新技能アンロック！**

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔤 **単語パック**
{vocab_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **文法奥義**
{grammar}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 **しんちゃんの一言**
「{shinchan_line}」
    """.strip()


def shinchan_vocab_card(vocab_list: list) -> str:
    """しんちゃん单词卡片"""
    lines = "\n".join([
        f"  **{v['japanese']}**（{v['kana']}）→ {v['meaning']}"
        f"\n  📝 {v['example']}（{v['example_meaning']}）"
        for v in vocab_list
    ])
    return f"""
📺 **しんちゃんの日本語教室**

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔤 **今日の単語**
{lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━
「覚えたらしんちゃんに自慢できるゾ！」
    """.strip()


def quiz_card(question: str, options: list) -> str:
    """选择题卡片"""
    opt_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
    return f"""
🎯 **練習問題**

{question}

{opt_text}
    """.strip()


def mission_complete(vocab_score: int, vocab_total: int,
                     listening_score: int, listening_total: int,
                     streak: int, xp: int, total_xp: int, level: str) -> str:
    """闯关完成战报"""
    return f"""
🎊 **ミッションクリア！お疲れ様！**

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **今日の戦績**
  ✅ 単語バトル  {vocab_score}/{vocab_total}
  ✅ 聴覚修行    {listening_score}/{listening_total}

🔥 連続学習：{streak} 日目！
💎 XP +{xp}（累計 {total_xp} XP）
🎖️ 称号：{level}

「継続は力なり！明日も待ってるぞ！」
    """.strip()


def status_report(xp: int, level: str, streak: int, max_streak: int,
                  current_lesson: str, progress_pct: int) -> str:
    """状态查询回复"""
    return f"""
📊 **現在のステータス**

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎖️ 称号：{level}
💎 XP：{xp}
🔥 現在の連続：{streak} 日
🏆 最長連続：{max_streak} 日

📚 **学習進捗**
  現在：{current_lesson}
  N5 進捗：{'█' * (progress_pct // 10)}{'░' * (10 - progress_pct // 10)} {progress_pct}%

「この調子で行こう！🔥」
    """.strip()


def shinchan_quote_random() -> str:
    """随机返回一条しんちゃん经典台词"""
    import random
    quotes = [
        ("オラはしんのすけ！", "我是新之助！"),
        ("おはよう！朝だゾ！", "早安！是早上了哦！"),
        ("ご飯まだ？お腹すいたゾ〜", "饭还没好吗？肚子饿了～"),
        ("みさえ〜　起きてよ〜", "美冴～起床了～"),
        ("オラ、ケーキが食べたいゾ！", "我想吃蛋糕！"),
        ("今日はいい天気だね〜", "今天天气真好呢～"),
        ("ねむすぎるゾ…", "太困了…"),
        ("楽しいことが一番だゾ！", "开心的事情最重要！"),
        ("ズル休みしようかな…", "要不要逃学呢…"),
        ("オラ、もう待てないゾ！", "我已经等不及了！"),
    ]
    jp, cn = random.choice(quotes)
    return f"🎬 **しんちゃんの一言**\n「{jp}」\n→ {cn}"

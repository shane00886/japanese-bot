"""
📢 每日推送服务 - 早安提醒 + 晚间战报
"""

import random
from datetime import datetime
from app.core.dingtalk import webhook_bot
from app.templates.course_data import N5_LESSONS


def push_morning():
    """早8点推送：每日任务提醒 + 打卡引导"""
    import requests
    from datetime import date

    today = date.today()
    # 用日期计算当天的课程（每3天1课）
    start_date = date(2026, 7, 20)  # 项目开始日期
    days_diff = (today - start_date).days
    lesson_idx = days_diff // 2  # 每2天1课
    if lesson_idx >= len(N5_LESSONS):
        lesson_idx = len(N5_LESSONS) - 1
    if lesson_idx < 0:
        lesson_idx = 0

    lesson = N5_LESSONS[lesson_idx]

    chapter = lesson["chapter"]
    title = lesson["title"]
    vocab_count = lesson["vocab_count"]
    shinchan_line = lesson.get("shinchan_line", "")

    msg = (
        f"🌅 **おはよう！しんちゃん先生からのミッション！**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **今日の修行**\n"
        f"章　：{chapter}\n"
        f"課　：{title}\n"
        f"単語：{vocab_count} 個\n\n"
        f"🎬 **しんちゃんの一言**\n"
        f"「{shinchan_line}」\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 **今日のやること**\n"
        f"1. 📖 打开 H5 页面学习 → https://japanese-bot-g5pq.onrender.com/learn\n"
        f"2. 🎤 跟着朗读，练习发音\n"
        f"3. ✅ 学完后回来对我说「打卡」！\n\n"
        f"💪 頑張れ！今日も一緒に日本語を勉強しよう！🔥"
    )

    try:
        webhook_bot.send_markdown("🌅 おはよう！今日のミッション", msg)
        print(f"✅ 早安推送成功（{lesson['title']}）")
    except Exception as e:
        print(f"❌ 早安推送失败: {e}")


def push_evening_report():
    """晚8点推送：今日学习战报"""
    import requests
    from app.models.database import get_connection
    from datetime import date

    today = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()

    # 获取今天打卡人数
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM checkins WHERE checkin_date = ?",
        (today,)
    )
    checkin_count = cursor.fetchone()["cnt"]

    # 获取今天最高连续天数
    cursor.execute(
        "SELECT MAX(streak_days) as max_streak FROM users"
    )
    max_streak = cursor.fetchone()["max_streak"] or 0

    # 获取活跃用户数
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE xp > 0"
    )
    active_users = cursor.fetchone()["cnt"]

    # 获取总注册用户
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cursor.fetchone()["cnt"]

    conn.close()

    # 计算今日课程
    start_date = date(2026, 7, 20)
    days_diff = (date.today() - start_date).days
    lesson_idx = days_diff // 2
    if lesson_idx >= len(N5_LESSONS):
        lesson_idx = len(N5_LESSONS) - 1
    if lesson_idx < 0:
        lesson_idx = 0
    lesson = N5_LESSONS[lesson_idx]

    # 推送战报
    msg = (
        f"📊 **今日の学習レポート**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **今日の課程**\n"
        f"{lesson['chapter']} → {lesson['title']}\n\n"
        f"👥 **グループ統計**\n"
        f"👤 総メンバー：{total_users} 人\n"
        f"✅ 今日打卡：{checkin_count} 人\n"
        f"🏆 最高連続：{max_streak} 日\n"
        f"🔥 アクティブ：{active_users} 人\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if checkin_count > 0:
        msg += f"\n🎉 今日 {checkin_count} 人が打卡しました！よく頑張った！\n"
    else:
        msg += f"\n😅 まだ打卡していない人は、忘れずに「打卡」と言ってね！\n"

    msg += (
        f"\n📌 明日も一緒に頑張ろう！\n"
        f"🔥 しんちゃんと日本語を学ぼう！"
    )

    try:
        webhook_bot.send_markdown("📊 今日の学習レポート", msg)
        print(f"✅ 晚间战报推送成功")
    except Exception as e:
        print(f"❌ 晚间战报推送失败: {e}")

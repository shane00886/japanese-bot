"""定时任务 — 每日自动推送"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.dingtalk import webhook_bot
from app.templates.messages import morning_teaser
from app.templates.course_data import N5_LESSONS


def morning_push():
    """每天早上 7:30 推送早安卡片"""
    lesson = N5_LESSONS[0] if N5_LESSONS else None
    if not lesson:
        return

    card = morning_teaser(
        lesson_title=lesson["title"],
        chapter=lesson["chapter"],
        duration=12,
        xp=25,
    )

    try:
        result = webhook_bot.send_markdown(
            "🌅 おはよう！師匠からのミッションだ！",
            card
        )
        if result.get("errcode") == 0:
            print(f"✅ 早安推送成功: {datetime.now()}")
        else:
            print(f"❌ 早安推送失败: {result}")
    except Exception as e:
        print(f"❌ 早安推送失败: {e}")


def setup_scheduler():
    """设置定时任务"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        morning_push,
        CronTrigger(hour=7, minute=30, timezone="Asia/Shanghai"),
        id="morning_push",
        name="早安日语卡片推送",
    )
    scheduler.start()
    print(f"⏰ 定时任务已启动: 每天 07:30 推送")
    return scheduler

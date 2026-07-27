"""定时任务 — 每日自动推送"""

from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.dingtalk import webhook_bot
from app.templates.messages import morning_teaser
from app.templates.course_data import N5_LESSONS

_scheduler = None


def morning_push():
    """每天早上 8:00 推送早安卡片到钉钉群"""
    lesson = N5_LESSONS[0] if N5_LESSONS else None
    if not lesson:
        print("⚠️ 没有课程数据，跳过推送")
        return

    card = morning_teaser(
        lesson_title=lesson["title"],
        chapter=lesson["chapter"],
        duration=12,
        xp=25,
    )

    try:
        result = webhook_bot.send_markdown(
            "🌅 早上好！师傅的任务来了！",
            card + "\n\n---\n📚 学习页面：https://japanese-bot-g5pq.onrender.com/learn"
        )
        if result.get("errcode") == 0:
            print(f"✅ 早安推送成功: {datetime.now()}")
        else:
            print(f"❌ 推送失败: {result}")
    except Exception as e:
        print(f"❌ 推送异常: {e}")


def setup_scheduler():
    """设置定时任务"""
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        morning_push,
        CronTrigger(hour=8, minute=0, timezone="Asia/Shanghai"),
        id="morning_push",
        name="每日早安推送",
        replace_existing=True,
    )
    _scheduler.start()
    print(f"⏰ 定时任务已启动: 每天 08:00 推送")

    # 启动后立即发送一次测试（部署验证）
    try:
        webhook_bot.send_markdown(
            "🤖 机器人上线啦！",
            "### 🤖 **机器人已上线！**\n\n"
            "以后每天早上 8:00 我会推送学习内容！\n\n"
            "📚 **试试跟我说：**\n"
            "  「任务」— 开始今天的学习\n"
            "  「打卡」— 记录完成\n"
            "  「进度」— 看看学到哪了\n"
            "  「帮助」— 查看所有功能\n\n"
            f"🌐 学习页面：https://japanese-bot-g5pq.onrender.com/learn"
        )
        print("✅ 上线消息已发送")
    except Exception as e:
        print(f"⚠️ 上线消息发送失败（正常，首次启动可能未配回调）: {e}")

    return _scheduler

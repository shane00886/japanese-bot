"""应用配置"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DINGTALK_APP_KEY: str = os.getenv("DINGTALK_APP_KEY", "")
    DINGTALK_APP_SECRET: str = os.getenv("DINGTALK_APP_SECRET", "")
    DINGTALK_AGENT_ID: str = os.getenv("DINGTALK_AGENT_ID", "")
    DINGTALK_WEBHOOK_URL: str = os.getenv("DINGTALK_WEBHOOK_URL", "")
    DINGTALK_WEBHOOK_SECRET: str = os.getenv("DINGTALK_WEBHOOK_SECRET", "")
    BOT_NAME: str = os.getenv("BOT_NAME", "しんちゃんの日本語先生")
    BASE_URL: str = os.getenv("BASE_URL", "https://japanese-bot-g5pq.onrender.com")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/jp_bot.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")


settings = Settings()

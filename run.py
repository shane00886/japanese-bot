#!/usr/bin/env python3
"""启动入口"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║     🤖 {settings.BOT_NAME}         ║
║     日本語学習ロボット                    ║
╚══════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )

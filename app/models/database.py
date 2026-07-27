"""数据库初始化"""

import sqlite3
import os
from pathlib import Path


DB_PATH = Path(__file__).parent.parent.parent / "data" / "jp_bot.db"


def get_connection() -> sqlite3.Connection:
    # 确保数据目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            level TEXT DEFAULT 'N5',
            xp INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            placement_score INTEGER,
            placement_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 课程表
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id TEXT PRIMARY KEY,
            level TEXT,
            lesson_no INTEGER,
            title TEXT,
            chapter TEXT,
            description TEXT,
            vocab_count INTEGER DEFAULT 0,
            grammar_points TEXT,
            shinchan_line TEXT
        );

        -- 词汇表
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id TEXT,
            japanese TEXT,
            kana TEXT,
            meaning TEXT,
            example TEXT,
            example_meaning TEXT,
            kanji TEXT,
            audio_url TEXT,
            FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id)
        );

        -- 单词掌握状态（间隔重复用）
        CREATE TABLE IF NOT EXISTS word_mastery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            word_id INTEGER,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 1,
            review_count INTEGER DEFAULT 0,
            correct_streak INTEGER DEFAULT 0,
            next_review_date TEXT,
            last_review_date TEXT,
            status TEXT DEFAULT 'learning',
            UNIQUE(user_id, word_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (word_id) REFERENCES vocabulary(id)
        );

        -- 每日学习记录
        CREATE TABLE IF NOT EXISTS daily_practice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            practice_date TEXT,
            lesson_id TEXT,
            type TEXT,
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            duration_minutes INTEGER DEFAULT 0,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, practice_date, type)
        );

        -- 打卡记录
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            checkin_date TEXT UNIQUE,
            completed INTEGER DEFAULT 1,
            xp_earned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 测试记录
        CREATE TABLE IF NOT EXISTS exams (
            exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            exam_type TEXT,
            exam_date TEXT,
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            detail_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 错题表
        CREATE TABLE IF NOT EXISTS wrong_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            word_id INTEGER,
            question TEXT,
            correct_answer TEXT,
            user_answer TEXT,
            lesson_id TEXT,
            wrong_count INTEGER DEFAULT 1,
            last_wrong_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        -- 初始测试记录
        CREATE TABLE IF NOT EXISTS placement_test (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            test_date TEXT,
            total_score INTEGER DEFAULT 0,
            listening_score INTEGER DEFAULT 0,
            vocabulary_score INTEGER DEFAULT 0,
            grammar_score INTEGER DEFAULT 0,
            detail_json TEXT,
            recommended_start TEXT
        );

        -- 会话日志
        CREATE TABLE IF NOT EXISTS chat_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message TEXT,
            response TEXT,
            intent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 投入度评分
        CREATE TABLE IF NOT EXISTS engagement_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            score_date TEXT UNIQUE,
            score INTEGER DEFAULT 100,
            signals_json TEXT,
            intervention_level INTEGER DEFAULT 0,
            intervention_applied TEXT
        );
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DB_PATH}")

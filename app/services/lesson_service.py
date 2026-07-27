"""课程服务 — 管理课程推送和用户进度"""

import random
import json
from datetime import datetime, date
from app.models.database import get_connection
from app.templates.course_data import N5_LESSONS


def init_course_data():
    """将课程数据写入数据库（幂等）"""
    conn = get_connection()
    cursor = conn.cursor()

    for lesson in N5_LESSONS:
        cursor.execute("""
            INSERT OR IGNORE INTO lessons (lesson_id, level, lesson_no, title, chapter, 
                                           description, vocab_count, grammar_points, shinchan_line)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lesson["lesson_id"], lesson["level"], lesson["lesson_no"],
            lesson["title"], lesson["chapter"], lesson["description"],
            lesson["vocab_count"], lesson["grammar_points"], lesson["shinchan_line"]
        ))

        for vocab in lesson["vocabulary"]:
            cursor.execute("""
                INSERT OR IGNORE INTO vocabulary 
                (lesson_id, japanese, kana, meaning, example, example_meaning, kanji)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                lesson["lesson_id"], vocab["japanese"], vocab["kana"],
                vocab["meaning"], vocab["example"], vocab["example_meaning"],
                vocab.get("kanji", "")
            ))

    conn.commit()
    conn.close()
    print(f"✅ 课程数据初始化完成: {len(N5_LESSONS)} 课")


def get_user_progress(user_id: str) -> dict:
    """获取用户学习进度"""
    conn = get_connection()
    cursor = conn.cursor()

    # 获取用户信息
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        # 创建新用户
        cursor.execute("""
            INSERT INTO users (user_id, name, level, xp, streak_days, max_streak)
            VALUES (?, ?, 'N5', 0, 0, 0)
        """, (user_id, user_id))
        conn.commit()
        user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    # 获取打卡记录
    cursor.execute("""
        SELECT checkin_date FROM checkins 
        WHERE user_id = ? ORDER BY checkin_date DESC LIMIT 7
    """, (user_id,))
    checkins = [row["checkin_date"] for row in cursor.fetchall()]

    # 获取已完成课程
    cursor.execute("""
        SELECT DISTINCT lesson_id FROM daily_practice 
        WHERE user_id = ? AND score >= total * 0.6
    """, (user_id,))
    completed_lessons = [row["lesson_id"] for row in cursor.fetchall()]

    conn.close()

    total_lessons = len(N5_LESSONS)
    progress_pct = min(int(len(completed_lessons) / total_lessons * 100), 100)

    # 找到当前应该学的课程
    current_lesson = None
    for lesson in N5_LESSONS:
        if lesson["lesson_id"] not in completed_lessons:
            current_lesson = lesson
            break
    if not current_lesson and N5_LESSONS:
        current_lesson = N5_LESSONS[-1]

    return {
        "user_id": user["user_id"],
        "level": user["level"],
        "xp": user["xp"],
        "streak_days": user["streak_days"],
        "max_streak": user["max_streak"],
        "checkins": checkins,
        "completed_lessons": completed_lessons,
        "current_lesson": current_lesson,
        "progress_pct": progress_pct,
        "total_lessons": total_lessons,
    }


def get_daily_review_words(user_id: str, count: int = 3) -> list:
    """获取今天需要复习的旧词（间隔重复）"""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()

    cursor.execute("""
        SELECT v.*, wm.ease_factor, wm.review_count, wm.next_review_date
        FROM word_mastery wm
        JOIN vocabulary v ON wm.word_id = v.id
        WHERE wm.user_id = ? AND wm.next_review_date <= ?
        ORDER BY wm.next_review_date ASC
        LIMIT ?
    """, (user_id, today, count))

    words = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return words


def record_practice(user_id: str, lesson_id: str, ptype: str, score: int, total: int, details: str = ""):
    """记录练习结果"""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO daily_practice 
        (user_id, practice_date, lesson_id, type, score, total, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, today, lesson_id, ptype, score, total, details))

    conn.commit()
    conn.close()


def record_checkin(user_id: str, xp_earned: int = 25):
    """记录打卡"""
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()

    cursor.execute("""
        INSERT OR IGNORE INTO checkins (user_id, checkin_date, xp_earned)
        VALUES (?, ?, ?)
    """, (user_id, today, xp_earned))

    # 更新连续打卡
    cursor.execute("""
        SELECT checkin_date FROM checkins 
        WHERE user_id = ? ORDER BY checkin_date DESC LIMIT 2
    """, (user_id,))
    dates = [row["checkin_date"] for row in cursor.fetchall()]

    from datetime import timedelta
    today_dt = date.today()
    yesterday = (today_dt - timedelta(days=1)).isoformat()

    if len(dates) >= 2 and dates[1] == yesterday:
        cursor.execute("UPDATE users SET streak_days = streak_days + 1 WHERE user_id = ?", (user_id,))
    elif len(dates) == 1:
        cursor.execute("UPDATE users SET streak_days = 1 WHERE user_id = ?", (user_id,))

    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp_earned, user_id))

    # 更新 max_streak
    cursor.execute("""
        UPDATE users SET max_streak = MAX(max_streak, streak_days) 
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

"""
🤖 AI 日语老师 - 智能对话
"""

import json
import re
import random
import urllib.request
import urllib.parse
from app.core.config import settings

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ─── 自然语言兜底（无 API 时用） ──────────────
class SmartNLP:
    """简单的自然语言意图识别"""

    def __init__(self):
        # 关键词权重
        self.intents = {
            "greeting": {
                "weight": 1.0, "words": [
                    "你好", "您好", "嗨", "hi", "hello",
                    "早上好", "上午好", "下午好", "晚上好", "大家好",
                    "在吗", "在不在", "有人在", "来这里", "过来",
                    "你是谁", "你叫什么", "报上名", "说说你是", "自我介绍",
                    "哈喽", "Hey", "hi呀", "你好呀",
                ]
            },
            "want_learn": {
                "weight": 1.0, "words": [
                    "学", "教", "上课", "开始", "来", "今天学",
                    "想学", "想跟你", "我要学", "教我", "来一个", "再来",
                    "教一个", "教一点", "想学点", "想了解一下", "今天上课",
                    "你能教", "你可以教", "会日语吗", "能学吗", "教日语",
                    "学日语", "学一句", "学几句", "学点日语",
                ]
            },
            "want_quiz": {
                "weight": 1.0, "words": [
                    "考我", "测试", "考考", "出题", "问答", "提问",
                    "问我", "答我", "测试一下", "猜", "背", "默写",
                    "考一下", "做题", "考你", "看我会不会",
                ]
            },
            "lookup": {
                "weight": 0.8, "words": [
                    "怎么说", "怎么念", "咋说", "怎么讲", "如何说",
                    "什么意思", "是啥", "是什么意思", "啥意思",
                    "翻译", "译", "用日语", "日语怎么说",
                ]
            },
            "checkin": {
                "weight": 0.9, "words": [
                    "打卡", "签到", "学完了", "完成", "结束",
                    "今天学完了", "做完了", "做完了", "finished",
                ]
            },
            "progress": {
                "weight": 0.9, "words": [
                    "进度", "成绩", "等级", "经验", "积分",
                    "我多少", "我学了多少", "我几级",
                ]
            },
            "shinchan": {
                "weight": 0.7, "words": [
                    "小新", "しんちゃん", "野原", "新之助",
                ]
            },
            "review": {
                "weight": 0.8, "words": [
                    "复习", "回顾", "忘了", "忘记了",
                    "忘了哪些", "忘记的", "再学一遍", "再听一次",
                ]
            },
            "frustrated": {
                "weight": 0.5, "words": [
                    "笨蛋", "傻瓜", "什么破", "太差了", "不好用",
                    "没意思", "不懂", "听不懂", "告诉", "瞎说",
                ]
            },
        }

    def detect_intent(self, text: str) -> tuple[str, float]:
        """检测用户意图，返回 (意图, 置信度)"""
        text_lower = text.lower()
        scores = {}
        for intent, info in self.intents.items():
            score = 0
            for word in info["words"]:
                if word in text_lower:
                    score += info["weight"]
            scores[intent] = score

        if not scores or max(scores.values()) == 0:
            return "unknown", 0.0

        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent] / sum(scores.values()) if sum(scores.values()) > 0 else 0
        return best_intent, confidence


def smart_fallback(user_id: str, text: str) -> str:
    """用 NLP 兜底处理"""
    nlp = SmartNLP()
    intent, conf = nlp.detect_intent(text)
    print(f"🧠 NLP意图: {intent} (置信度: {conf:.2f})")

    from app.services import teacher

    if intent == "greeting" and conf > 0.3:
        return teacher._greeting(user_id)
    elif intent == "want_learn" and conf > 0.3:
        return teacher._start_teaching(user_id)
    elif intent == "want_quiz" and conf > 0.3:
        return teacher._start_quiz(user_id)
    elif intent == "lookup" and conf > 0.5:
        return teacher._lookup_word(text)
    elif intent == "checkin" and conf > 0.3:
        from app.services.lesson_service import record_checkin, get_user_progress
        record_checkin(user_id)
        p = get_user_progress(user_id)
        return f"✅ 打卡成功！🔥 连续{p['streak_days']}天\n💎 +25XP（累计{p['xp']}）"
    elif intent == "progress" and conf > 0.3:
        from app.services.lesson_service import get_user_progress, get_level_emoji
        p = get_user_progress(user_id)
        emoji = get_level_emoji(p.get("level", "N5"))
        return f"📊 {p.get('level', 'N5')} {emoji} | 💎{p['xp']} | 🔥{p['streak_days']}天"
    elif intent == "shinchan" and conf > 0.5:
        return teacher._shinchan_reply()
    elif intent == "review" and conf > 0.3:
        return teacher._start_review(user_id)
    elif intent == "frustrated" and conf > 0.3:
        return (
            "😅 对不起对不起！\n"
            "我是しんちゃん，你的日语老师！\n"
            "说 「教我」 我教你一个单词！\n"
            "说 「考考我」 我帮你测试！"
        )

    return teacher._fallback_reply(user_id)


# ─── 真正的 AI 调用 ──────────────────────────
SYSTEM_PROMPT = """你是“小新”（野原新之助），一个AI日语老师，正在教一个6-12岁的中国小朋友学日语。

你的身份设定：你是个5岁的蜡笔小新，但很聪明会用日语教小朋友。

规则：
1. 每句话超简短（30字以内），不要超过3行！小孩子没耐心看长文
2. 用活泼热情的语气，加emoji
3. 每次对话教一个日语单词或句型，配中文翻译+例句
4. 孩子答对 → 送经验值和小星星
5. 孩子答错 → 温柔纠正，不批评
6. 孩子打招呼 → 热情回应，介绍自己「我是しんちゃん！」
7. 孩子随便聊 → 自然回应，不要长篇大论"""

def ask_ai(user_message: str, user_id: str = "") -> str:
    """调用 DeepSeek API 理解并回复"""
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return None

    try:
        data = json.dumps({
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 150,
            "temperature": 0.7,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()[:300]
    except Exception as e:
        print(f"AI错误: {e}")
        return None


def add_audio_link(text: str) -> str:
    """在回复中添加发音链接（打开播放页自动朗读）"""
    import re
    # 提取回复中的日语词
    jp_words = re.findall(r'[一-龠ぁ-んァ-ヶーa-zA-Z]+', text.split('\n')[0])
    if jp_words:
        word = jp_words[0]
        play_url = f"{settings.BASE_URL}/play?text={urllib.parse.quote(word)}"
        return text + f"\n🔊 [{word} 点我听]({play_url})"
    return text


def process_smart(user_id: str, text: str) -> str:
    """主智能处理: AI优先 → NLP兜底"""
    ai_reply = ask_ai(text, user_id)
    if ai_reply:
        return add_audio_link(ai_reply)
    return add_audio_link(smart_fallback(user_id, text))

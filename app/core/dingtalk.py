"""钉钉 API 客户端"""

import time
import json
import hmac
import hashlib
import base64
import urllib.parse
import requests
from typing import Optional
from app.core.config import settings


class DingTalkClient:
    """钉钉开放平台 API 封装"""

    def __init__(self):
        self.app_key = settings.DINGTALK_APP_KEY
        self.app_secret = settings.DINGTALK_APP_SECRET
        self.agent_id = settings.DINGTALK_AGENT_ID
        self._token: Optional[str] = None
        self._token_expire: float = 0
        self.base_url = "https://api.dingtalk.com"

    def _get_token(self) -> str:
        """获取 access_token（带缓存）"""
        if self._token and time.time() < self._token_expire:
            return self._token

        url = f"{self.base_url}/v1.0/oauth2/accessToken"
        payload = {"appKey": self.app_key, "appSecret": self.app_secret}
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("accessToken", "")
        # 提前 5 分钟刷新
        self._token_expire = time.time() + data.get("expireIn", 7200) - 300
        return self._token

    def _headers(self) -> dict:
        return {
            "x-acs-dingtalk-access-token": self._get_token(),
            "Content-Type": "application/json",
        }

    def send_markdown_message(
        self, user_id: str, title: str, text: str, robot_code: Optional[str] = None
    ) -> dict:
        """向指定用户发送 Markdown 消息（单聊）"""
        url = f"{self.base_url}/v1.0/robot/oToMessages/batchSend"
        payload = {
            "robotCode": self.agent_id,
            "userIds": [user_id],
            "msgKey": "sampleMarkdown",
            "msgParam": json.dumps({"title": title, "text": text}),
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        return resp.json()

    def send_group_markdown(
        self, open_conversation_id: str, title: str, text: str
    ) -> dict:
        """向指定群发送 Markdown 消息"""
        url = f"{self.base_url}/v1.0/robot/groupMessages/send"
        payload = {
            "robotCode": self.agent_id,
            "openConversationId": open_conversation_id,
            "msgKey": "sampleMarkdown",
            "msgParam": json.dumps({"title": title, "text": text}),
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        return resp.json()

    def send_group_action_card(
        self, open_conversation_id: str, title: str, text: str,
        single_title: str = "开始闯关！", single_url: str = "",
        btn_orientation: str = "1"
    ) -> dict:
        """向群发送 ActionCard 互动卡片"""
        url = f"{self.base_url}/v1.0/robot/groupMessages/send"
        card_data = {
            "title": title,
            "text": text,
            "btnOrientation": btn_orientation,
        }
        if single_url:
            card_data["singleTitle"] = single_title
            card_data["singleURL"] = single_url
        else:
            card_data["btns"] = [
                {"title": "开始闯关！", "actionURL": "https://www.dingtalk.com"},
                {"title": "查看单词表", "actionURL": "https://www.dingtalk.com"},
            ]

        payload = {
            "robotCode": self.agent_id,
            "openConversationId": open_conversation_id,
            "msgKey": "sampleActionCard",
            "msgParam": json.dumps(card_data),
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        return resp.json()

    def get_user_info(self, user_id: str) -> dict:
        """获取用户信息"""
        url = f"{self.base_url}/v1.0/contact/users/{user_id}"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        return resp.json()


class WebhookBot:
    """群自定义机器人（Webhook 方式发送，用于推送消息到群）"""

    def __init__(self):
        self.webhook_url = settings.DINGTALK_WEBHOOK_URL
        self.secret = settings.DINGTALK_WEBHOOK_SECRET

    def _sign_url(self) -> str:
        """生成带签名的 URL"""
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote(base64.b64encode(hmac_code))
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send_markdown(self, title: str, text: str) -> dict:
        """发送 Markdown 消息到群"""
        url = self._sign_url()
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json()

    def send_text(self, content: str) -> dict:
        """发送纯文本消息"""
        url = self._sign_url()
        payload = {"msgtype": "text", "text": {"content": content}}
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json()


# 全局单例
ding_client = DingTalkClient()
webhook_bot = WebhookBot()

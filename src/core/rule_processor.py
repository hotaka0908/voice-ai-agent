"""
Rule Processor - ルールベース処理システム

AIの回答前に特定のパターンに対してルールベースで応答を生成
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger


class RuleProcessor:
    """ルールベース処理を行うクラス"""

    def __init__(self):
        self.rules = self._load_rules()
        self.initialized = False

    def _load_rules(self) -> List[Dict[str, Any]]:
        """ルール定義を読み込み"""
        return [
            # 挨拶系
            {
                "name": "greeting_morning",
                "patterns": [r"おはよう", r"お早う", r"^morning$", r"^ohayo"],
                "responses": [
                    "おはようございます！今日も一日頑張りましょう！",
                    "おはよう！素敵な一日になりそうですね",
                    "おはようございます。今日はどんなことをお手伝いしましょうか？"
                ],
                "priority": 10
            },
            {
                "name": "greeting_general",
                "patterns": [r"こんにちは", r"こんばんは", r"hello", r"hi"],
                "responses": [
                    "こんにちは！何かお手伝いできることはありますか？",
                    "こんにちは！今日はいかがお過ごしですか？",
                    "お疲れさまです！何でもお気軽にお聞かせください"
                ],
                "priority": 10
            },

            # 時間関連の質問
            {
                "name": "current_time",
                "patterns": [r"今何時", r"時間.*教えて", r"現在.*時刻", r"いまの時間"],
                "responses": [],  # 動的生成
                "action": "get_current_time",
                "priority": 15
            },
            {
                "name": "current_date",
                "patterns": [r"今日.*日付", r"今日.*何日", r"日付.*教えて", r"きょうの日付"],
                "responses": [],
                "action": "get_current_date",
                "priority": 15
            },

            # 計算系（簡単な計算）
            {
                "name": "simple_calculation",
                "patterns": [r"(\d+)\s*\+\s*(\d+)", r"(\d+)\s*-\s*(\d+)",
                           r"(\d+)\s*×\s*(\d+)", r"(\d+)\s*÷\s*(\d+)"],
                "responses": [],
                "action": "calculate",
                "priority": 20
            },

            # 感情・気分関連
            {
                "name": "feeling_bad",
                "patterns": [r"疲れた", r"つらい", r"大変", r"きつい", r"しんどい"],
                "responses": [
                    "お疲れさまです。少し休憩してくださいね",
                    "大変でしたね。無理をしないでください",
                    "お疲れのようですね。何かリラックスできることはありますか？"
                ],
                "priority": 8
            },
            {
                "name": "feeling_good",
                "patterns": [r"嬉しい", r"楽しい", r"良い", r"最高", r"幸せ"],
                "responses": [
                    "それは良かったです！素晴らしいですね",
                    "嬉しいお話をありがとうございます！",
                    "そんな気持ちになれて良かったですね"
                ],
                "priority": 8
            },

            # お礼・謝罪
            {
                "name": "thanks",
                "patterns": [r"ありがとう", r"感謝", r"thank"],
                "responses": [
                    "どういたしまして。ではまた後ほど。"
                ],
                "priority": 12
            },
            {
                "name": "sorry",
                "patterns": [r"ごめん", r"すみません", r"申し訳", r"sorry"],
                "responses": [
                    "大丈夫ですよ！",
                    "お気になさらず",
                    "いえいえ、全然問題ありません"
                ],
                "priority": 12
            },

            # システム関連
            {
                "name": "help",
                "patterns": [r"ヘルプ", r"使い方", r"help", r"どうやって", r"方法"],
                "responses": [
                    "私は音声AIアシスタントです。話しかけてくだされば、様々なお手伝いができます",
                    "マイクボタンを押して話しかけてください。質問、計算、情報検索などができます",
                    "設定画面から個人情報を登録すると、よりパーソナライズされた応答ができます"
                ],
                "priority": 15
            },

            # Gmail関連（最高優先度）
            {
                "name": "gmail_trigger",
                "patterns": [r"メール", r"gmail", r"ジーメール", r"Gmailについて", r"メールチェック",
                           r"受信.*メール", r"送信.*メール", r"メール.*確認", r"メール.*読", r"メール.*送",
                           r"返信", r"メール.*返信", r"返事", r"メール.*返事", r"reply"],
                "responses": [],
                "action": "use_gmail_tool",
                "priority": 25  # 最高優先度
            },

            # 終了・さようなら
            {
                "name": "goodbye",
                "patterns": [r"さようなら", r"バイバイ", r"また.*", r"bye", r"goodbye"],
                "responses": [
                    "さようなら！また話しましょう",
                    "お疲れさまでした！またお会いしましょう",
                    "また今度お話ししましょう。お気をつけて！"
                ],
                "priority": 10
            }
        ]

    async def initialize(self):
        """初期化"""
        self.initialized = True
        logger.info("Rule Processor initialized successfully")

    async def process_input(self, user_input: str, context: Dict = None, memory_tool=None) -> Optional[Dict[str, Any]]:
        """
        ユーザー入力をルールベース処理

        Args:
            user_input: ユーザーの入力テキスト
            context: 会話コンテキスト

        Returns:
            ルールにマッチした場合の応答データ、マッチしない場合はNone
        """
        if not self.initialized:
            return None

        user_input_clean = user_input.strip().lower()
        matched_rule = None
        highest_priority = -1

        # 優先度順でルールをチェック
        for rule in self.rules:
            for pattern in rule["patterns"]:
                if re.search(pattern, user_input_clean, re.IGNORECASE):
                    if rule["priority"] > highest_priority:
                        matched_rule = rule
                        highest_priority = rule["priority"]
                        break

        if not matched_rule:
            return None

        try:
            # アクションがある場合は実行
            if "action" in matched_rule:
                # Gmailキーワードのときはツール提案を返す（LLMに依存せず実行可能にする）
                if matched_rule["action"] == "use_gmail_tool":
                    tool_calls = self._suggest_gmail_tool_calls(user_input_clean)
                    return {
                        "rule_name": matched_rule["name"],
                        "response": "",
                        "priority": matched_rule["priority"],
                        "is_final": False,
                        "tool_calls": tool_calls,
                    }

                response_text = await self._execute_action(matched_rule["action"], user_input_clean, memory_tool)

            else:
                # 固定応答からランダム選択（個人情報を考慮）
                import random
                response_text = random.choice(matched_rule["responses"])

                # 個人情報がある場合はパーソナライズ
                if memory_tool:
                    response_text = await self._personalize_response(response_text, matched_rule["name"], memory_tool)

            return {
                "rule_name": matched_rule["name"],
                "response": response_text,
                "priority": matched_rule["priority"],
                "is_final": True  # ルールベース応答は最終応答とする
            }

        except Exception as e:
            logger.error(f"Rule processing error: {e}")
            return None

    def _suggest_gmail_tool_calls(self, user_input: str) -> List[Dict[str, Any]]:
        """Gmail関連入力に対して適切なツール呼び出しを提案"""
        # 返信関連のキーワード
        reply_keywords = ["返信", "返事", "reply"]
        # 未読や読み取り関連のキーワード
        read_keywords = ["未読", "読", "内容", "確認", "開いて", "チェック"]
        list_keywords = ["一覧", "リスト", "何件", "最新", "件数"]

        # 返信要求の場合は最新メールを読んで返信準備
        if any(k in user_input for k in reply_keywords):
            # 返信内容を抽出
            reply_content = self._extract_reply_content(user_input)

            # 返信要求の場合は2段階処理：メール一覧取得 → 返信実行
            return [
                {
                    "name": "gmail",
                    "parameters": {"action": "list", "max_results": 1}
                },
                {
                    "name": "gmail",
                    "parameters": {
                        "action": "reply",
                        "message_id": "メールID",  # プレースホルダー
                        "body": reply_content or "了解しました。"
                    }
                }
            ]

        if any(k in user_input for k in read_keywords):
            # 未読を優先してメール一覧を取得（未読が無ければ最新5件）
            return [{
                "name": "gmail",
                "parameters": {"action": "list", "query": "is:unread", "max_results": 5}
            }]

        # それ以外は一覧（最新5件）
        return [{
            "name": "gmail",
            "parameters": {"action": "list", "max_results": 5}
        }]

    async def _execute_action(self, action: str, user_input: str, memory_tool=None) -> str:
        """アクション実行"""
        if action == "get_current_time":
            now = datetime.now()
            return f"現在の時刻は{now.strftime('%H時%M分')}です"

        elif action == "get_current_date":
            now = datetime.now()
            weekday = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
            return f"今日は{now.strftime('%Y年%m月%d日')}（{weekday}曜日）です"

        elif action == "calculate":
            return await self._simple_calculate(user_input)

        elif action == "use_gmail_tool":
            return None  # ルールベース処理をスキップしてAI処理に移行

        return "処理できませんでした"

    def _extract_reply_content(self, user_input: str) -> str:
        """返信内容を抽出"""
        import re

        # 返信内容のパターンを検索
        patterns = [
            r'(.+?)って返信',
            r'(.+?)と返信',
            r'(.+?)て返信',
            r'(.+?)って返事',
            r'(.+?)と返事',
            r'(.+?)て返事'
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                content = match.group(1).strip()
                # 不要な部分を除去
                content = re.sub(r'^(メールに|最新のメールに|)', '', content)
                if content:
                    return content

        # パターンにマッチしない場合は全体をチェック
        if "返信" in user_input or "返事" in user_input:
            # 「返信して」の前の部分を抽出
            parts = re.split(r'(って|と|て)?(返信|返事)', user_input)
            if parts and parts[0].strip():
                content = parts[0].strip()
                content = re.sub(r'^(メールに|最新のメールに|)', '', content)
                if content and content not in ["届いてる", "わかった", "了解"]:
                    return content

        return "了解しました。"

    async def _simple_calculate(self, user_input: str) -> str:
        """簡単な計算処理"""
        try:
            # 足し算
            match = re.search(r'(\d+)\s*\+\s*(\d+)', user_input)
            if match:
                a, b = int(match.group(1)), int(match.group(2))
                return f"{a} + {b} = {a + b}です"

            # 引き算
            match = re.search(r'(\d+)\s*-\s*(\d+)', user_input)
            if match:
                a, b = int(match.group(1)), int(match.group(2))
                return f"{a} - {b} = {a - b}です"

            # 掛け算
            match = re.search(r'(\d+)\s*[×*]\s*(\d+)', user_input)
            if match:
                a, b = int(match.group(1)), int(match.group(2))
                return f"{a} × {b} = {a * b}です"

            # 割り算
            match = re.search(r'(\d+)\s*[÷/]\s*(\d+)', user_input)
            if match:
                a, b = int(match.group(1)), int(match.group(2))
                if b != 0:
                    result = a / b
                    if result == int(result):
                        return f"{a} ÷ {b} = {int(result)}です"
                    else:
                        return f"{a} ÷ {b} = {result:.2f}です"
                else:
                    return "0で割ることはできません"

        except Exception as e:
            logger.error(f"Calculation error: {e}")

        return "計算できませんでした"

    async def _personalize_response(self, response: str, rule_name: str, memory_tool) -> str:
        """個人情報に基づいて応答をパーソナライズ"""
        if not memory_tool:
            return response

        try:
            personal_info = await memory_tool.get_personal_info()
            if not personal_info:
                return response

            # 名前がある場合は挨拶に名前を追加
            if rule_name in ["greeting_morning", "greeting_general"] and "name" in personal_info:
                if "おはよう" in response:
                    return f"おはようございます、{personal_info['name']}さん！今日も一日頑張りましょう！"
                elif "こんにちは" in response:
                    return f"こんにちは、{personal_info['name']}さん！今日はいかがお過ごしですか？"

            # お礼応答に名前を追加
            elif rule_name == "thanks" and "name" in personal_info:
                return f"どういたしまして、{personal_info['name']}さん。ではまた後ほど。"

            # 趣味に関連した応答
            elif rule_name == "feeling_good" and "hobbies" in personal_info:
                return f"それは良かったです！{personal_info['hobbies']}の時間でも作って、さらに楽しい時間を過ごしてくださいね。"

            return response

        except Exception as e:
            logger.error(f"Failed to personalize response: {e}")
            return response

    def add_rule(self, rule: Dict[str, Any]):
        """ルールを追加"""
        self.rules.append(rule)
        # 優先度順にソート
        self.rules.sort(key=lambda x: x.get("priority", 0), reverse=True)
        logger.info(f"Added rule: {rule.get('name', 'unnamed')}")

    def get_rule_stats(self) -> Dict[str, Any]:
        """ルール統計情報を取得"""
        return {
            "total_rules": len(self.rules),
            "rule_names": [rule.get("name", "unnamed") for rule in self.rules],
            "initialized": self.initialized
        }

    async def cleanup(self):
        """クリーンアップ"""
        self.initialized = False
        logger.info("Rule Processor cleanup completed")

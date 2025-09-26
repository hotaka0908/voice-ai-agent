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

    async def process_input(self, user_input: str, context: Dict = None) -> Optional[Dict[str, Any]]:
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
                response_text = await self._execute_action(matched_rule["action"], user_input_clean)
            else:
                # 固定応答からランダム選択
                import random
                response_text = random.choice(matched_rule["responses"])

            return {
                "rule_name": matched_rule["name"],
                "response": response_text,
                "priority": matched_rule["priority"],
                "is_final": True  # ルールベース応答は最終応答とする
            }

        except Exception as e:
            logger.error(f"Rule processing error: {e}")
            return None

    async def _execute_action(self, action: str, user_input: str) -> str:
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

        return "処理できませんでした"

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
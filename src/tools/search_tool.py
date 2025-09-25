"""
Search Tool - 検索ツール

Web検索や情報検索を実行するツール
"""

import aiohttp
from typing import Dict, Any, List
from loguru import logger

from src.core.tool_base import Tool, ToolResult, ToolParameter


class SearchTool(Tool):
    """Web検索を実行するツール"""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "インターネットで情報を検索します"

    @property
    def category(self) -> str:
        return "information"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="検索クエリ",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="検索結果の最大件数（1-10、デフォルト：5）",
                required=False,
                default=5
            )
        ]

    async def _initialize_impl(self):
        """検索ツールの初期化"""
        # 検索API設定（実際には使用できるAPI キーが必要）
        import os
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX")
        self.serp_api_key = os.getenv("SERP_API_KEY")

        # APIキーが設定されていない場合はモックモード
        self.mock_mode = not (self.google_api_key and self.google_cx)

        if self.mock_mode:
            logger.warning("No search API keys configured, using mock search results")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """検索を実行して結果を返す"""
        try:
            query = parameters.get("query", "").strip()
            limit = min(int(parameters.get("limit", 5)), 10)

            if not query:
                return ToolResult(
                    success=False,
                    result=None,
                    error="検索クエリが指定されていません"
                )

            if self.mock_mode:
                results = await self._mock_search(query, limit)
            else:
                results = await self._real_search(query, limit)

            return ToolResult(
                success=True,
                result=results,
                metadata={
                    "query": query,
                    "limit": limit,
                    "mode": "mock" if self.mock_mode else "real"
                }
            )

        except Exception as e:
            logger.error(f"Search tool execution failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=f"検索の実行に失敗しました: {str(e)}"
            )

    async def _real_search(self, query: str, limit: int) -> str:
        """実際のAPIを使用して検索"""
        try:
            if self.google_api_key and self.google_cx:
                return await self._google_search(query, limit)
            elif self.serp_api_key:
                return await self._serp_search(query, limit)
            else:
                return await self._mock_search(query, limit)

        except Exception as e:
            logger.error(f"Real search failed, falling back to mock: {e}")
            return await self._mock_search(query, limit)

    async def _google_search(self, query: str, limit: int) -> str:
        """Google Custom Search APIを使用"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "num": limit,
            "hl": "ja"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"Google Search API error: {response.status}")

                data = await response.json()
                return self._format_search_results(data.get("items", []), query)

    async def _serp_search(self, query: str, limit: int) -> str:
        """SerpAPI を使用（代替API）"""
        url = "https://serpapi.com/search.json"
        params = {
            "api_key": self.serp_api_key,
            "engine": "google",
            "q": query,
            "num": limit,
            "hl": "ja"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"SerpAPI error: {response.status}")

                data = await response.json()
                return self._format_serp_results(data.get("organic_results", []), query)

    async def _mock_search(self, query: str, limit: int) -> str:
        """モック検索結果を生成"""
        # 簡易的なキーワードベースの結果生成
        mock_results = []

        # よくある検索クエリに対する模擬回答
        common_queries = {
            "天気": [
                {"title": "気象庁 | 天気予報", "snippet": "全国の天気予報、天気図、台風情報、降雨情報などを提供", "url": "https://www.jma.go.jp/"},
                {"title": "Yahoo!天気", "snippet": "全国各地の天気予報、雨雲の動き、注意報・警報を確認できます", "url": "https://weather.yahoo.co.jp/"},
            ],
            "ニュース": [
                {"title": "NHK NEWS WEB", "snippet": "NHKのニュースサイト。国内外の取材網を生かし、さまざまな分野のニュースを発信", "url": "https://www3.nhk.or.jp/news/"},
                {"title": "朝日新聞デジタル", "snippet": "朝日新聞社のニュースサイト。政治、経済、社会、国際、スポーツ、科学、文化・芸能などの速報ニュース", "url": "https://www.asahi.com/"},
            ],
            "レシピ": [
                {"title": "クックパッド", "snippet": "日本最大の料理レシピサービス。350万品以上のレシピ、作り方を検索できる", "url": "https://cookpad.com/"},
                {"title": "味の素レシピ大百科", "snippet": "味の素が提供するレシピサイト。プロの料理家によるレシピが豊富", "url": "https://park.ajinomoto.co.jp/recipe/"},
            ]
        }

        # キーワードマッチング
        for keyword, results in common_queries.items():
            if keyword in query:
                mock_results.extend(results[:limit])
                break

        # 一般的な結果がない場合は汎用的な結果を生成
        if not mock_results:
            for i in range(limit):
                mock_results.append({
                    "title": f"{query} - 検索結果 {i+1}",
                    "snippet": f"{query}に関する情報をお探しですか？こちらのサイトでは{query}について詳しく解説しています。",
                    "url": f"https://example.com/search/{i+1}"
                })

        return self._format_mock_results(mock_results, query)

    def _format_search_results(self, items: List[Dict], query: str) -> str:
        """Google検索結果をフォーマット"""
        if not items:
            return f"🔍 '{query}' の検索結果が見つかりませんでした"

        result_text = f"🔍 '{query}' の検索結果 ({len(items)}件):\n\n"

        for i, item in enumerate(items, 1):
            title = item.get("title", "タイトルなし")
            snippet = item.get("snippet", "説明なし")
            url = item.get("link", "")

            # スニペットを短縮
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."

            result_text += f"{i}. **{title}**\n"
            result_text += f"   {snippet}\n"
            result_text += f"   🔗 {url}\n\n"

        return result_text.strip()

    def _format_serp_results(self, results: List[Dict], query: str) -> str:
        """SerpAPI結果をフォーマット"""
        if not results:
            return f"🔍 '{query}' の検索結果が見つかりませんでした"

        result_text = f"🔍 '{query}' の検索結果 ({len(results)}件):\n\n"

        for i, result in enumerate(results, 1):
            title = result.get("title", "タイトルなし")
            snippet = result.get("snippet", "説明なし")
            url = result.get("link", "")

            # スニペットを短縮
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."

            result_text += f"{i}. **{title}**\n"
            result_text += f"   {snippet}\n"
            result_text += f"   🔗 {url}\n\n"

        return result_text.strip()

    def _format_mock_results(self, results: List[Dict], query: str) -> str:
        """モック検索結果をフォーマット"""
        result_text = f"🔍 '{query}' の検索結果 ({len(results)}件) [デモモード]:\n\n"

        for i, result in enumerate(results, 1):
            title = result.get("title", "タイトルなし")
            snippet = result.get("snippet", "説明なし")
            url = result.get("url", "")

            result_text += f"{i}. **{title}**\n"
            result_text += f"   {snippet}\n"
            result_text += f"   🔗 {url}\n\n"

        result_text += "\n💡 実際の検索を行うには、Google Search APIキーを設定してください。"

        return result_text.strip()

    async def search_news(self, query: str) -> str:
        """ニュース検索（特化版）"""
        news_query = f"{query} ニュース site:nhk.or.jp OR site:asahi.com OR site:mainichi.jp"
        return await self._real_search(news_query, 5)

    async def search_images(self, query: str) -> str:
        """画像検索（URLのみ）"""
        # 実際のAPIでは画像検索結果のURLを返す
        return f"🖼️ '{query}' の画像検索はWebインターフェースをご利用ください"
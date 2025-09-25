"""
Personal Memory - パーソナル学習エンジン

RAGとベクトルDBを使用してユーザーとの会話を記憶・学習し、
関連情報を検索して個人適応型の応答を提供するシステム
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, using mock vector database")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence Transformers not available")

import asyncio


class PersonalMemory:
    """
    パーソナル学習エンジン

    ユーザーとの会話を記憶し、関連情報を検索してパーソナライズされた応答を提供
    """

    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.encoder = None
        self.is_initialized = False

        # 設定
        self.config = {
            "collection_name": "user_memory",
            "embedding_model": "all-MiniLM-L6-v2",
            "max_memory_entries": 10000,
            "memory_retention_days": 365,
            "similarity_threshold": 0.7,
            "max_search_results": 5,
            "db_path": "./data/memory/chroma_db"
        }

        # メモリカテゴリ
        self.memory_categories = {
            "conversation": "会話履歴",
            "preference": "ユーザー設定",
            "fact": "事実情報",
            "instruction": "指示・学習内容",
            "context": "文脈情報"
        }

    async def initialize(self):
        """パーソナルメモリシステムの初期化"""
        try:
            logger.info("Initializing Personal Memory system...")

            # 環境変数から設定を読み込み
            self.config.update({
                "db_path": os.getenv("VECTOR_DB_PATH", self.config["db_path"]),
                "max_memory_entries": int(os.getenv("MAX_MEMORY_ENTRIES", self.config["max_memory_entries"])),
                "memory_retention_days": int(os.getenv("MEMORY_RETENTION_DAYS", self.config["memory_retention_days"]))
            })

            # データベースディレクトリの作成
            os.makedirs(self.config["db_path"], exist_ok=True)

            # ChromaDBの初期化
            if CHROMADB_AVAILABLE:
                await self._initialize_chromadb()
            else:
                await self._initialize_mock_db()

            # 文章エンコーダーの初期化
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                await self._initialize_encoder()

            # 古いメモリのクリーンアップ
            await self._cleanup_old_memories()

            self.is_initialized = True
            logger.info("Personal Memory system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Personal Memory system: {e}")
            raise

    async def _initialize_chromadb(self):
        """ChromaDBの初期化"""
        try:
            # ChromaDBクライアントの作成
            self.chroma_client = chromadb.PersistentClient(
                path=self.config["db_path"],
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # コレクションの取得または作成
            try:
                self.collection = self.chroma_client.get_collection(
                    name=self.config["collection_name"]
                )
                logger.info(f"Loaded existing collection: {self.config['collection_name']}")
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.config["collection_name"],
                    metadata={"description": "Personal memory and conversation history"}
                )
                logger.info(f"Created new collection: {self.config['collection_name']}")

            # コレクションの統計情報を取得
            count = self.collection.count()
            logger.info(f"Current memory entries: {count}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    async def _initialize_mock_db(self):
        """モックデータベースの初期化"""
        logger.info("Using mock vector database")
        self.mock_memories = []

        # 既存のモックデータを読み込み
        mock_file = os.path.join(self.config["db_path"], "mock_memories.json")
        try:
            if os.path.exists(mock_file):
                with open(mock_file, 'r', encoding='utf-8') as f:
                    self.mock_memories = json.load(f)
                logger.info(f"Loaded {len(self.mock_memories)} mock memory entries")
        except Exception as e:
            logger.warning(f"Failed to load mock memories: {e}")
            self.mock_memories = []

    async def _initialize_encoder(self):
        """文章エンコーダーの初期化"""
        try:
            logger.info(f"Loading sentence transformer model: {self.config['embedding_model']}")

            # 非同期でモデルを読み込み
            loop = asyncio.get_event_loop()
            self.encoder = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.config["embedding_model"]
            )

            logger.info("Sentence transformer model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize encoder: {e}")
            self.encoder = None

    async def store_interaction(self, user_input: str, assistant_response: str) -> bool:
        """
        ユーザーとの会話を記憶に保存

        Args:
            user_input: ユーザーの入力
            assistant_response: アシスタントの応答

        Returns:
            保存成功かどうか
        """
        if not self.is_initialized:
            logger.warning("Personal Memory not initialized")
            return False

        try:
            timestamp = datetime.now()

            # ユーザー入力を保存
            user_memory = {
                "content": user_input,
                "role": "user",
                "category": "conversation",
                "timestamp": timestamp.isoformat(),
                "metadata": {
                    "length": len(user_input),
                    "type": "user_input"
                }
            }

            await self._store_memory_entry(user_memory)

            # アシスタント応答を保存
            assistant_memory = {
                "content": assistant_response,
                "role": "assistant",
                "category": "conversation",
                "timestamp": timestamp.isoformat(),
                "metadata": {
                    "length": len(assistant_response),
                    "type": "assistant_response",
                    "related_user_input": hashlib.md5(user_input.encode()).hexdigest()[:8]
                }
            }

            await self._store_memory_entry(assistant_memory)

            logger.debug("Interaction stored successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")
            return False

    async def _store_memory_entry(self, memory: Dict[str, Any]):
        """単一のメモリエントリを保存"""
        try:
            content = memory["content"]
            memory_id = hashlib.md5(
                f"{content}{memory['timestamp']}".encode()
            ).hexdigest()

            if self.chroma_client and self.collection:
                # ChromaDBに保存
                self.collection.add(
                    documents=[content],
                    metadatas=[{k: v for k, v in memory.items() if k != "content"}],
                    ids=[memory_id]
                )
            else:
                # モックDBに保存
                memory["id"] = memory_id
                self.mock_memories.append(memory)

                # ファイルに保存
                await self._persist_mock_memories()

        except Exception as e:
            logger.error(f"Failed to store memory entry: {e}")
            raise

    async def search_relevant(self, query: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        クエリに関連するメモリを検索

        Args:
            query: 検索クエリ
            limit: 結果の最大数

        Returns:
            関連するメモリのリスト
        """
        if not self.is_initialized:
            return []

        limit = limit or self.config["max_search_results"]

        try:
            if self.chroma_client and self.collection:
                return await self._search_chromadb(query, limit)
            else:
                return await self._search_mock_db(query, limit)

        except Exception as e:
            logger.error(f"Failed to search relevant memories: {e}")
            return []

    async def _search_chromadb(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """ChromaDBでの検索"""
        try:
            # ベクトル検索を実行
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )

            memories = []
            if results["documents"] and len(results["documents"]) > 0:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]

                for doc, metadata, distance in zip(documents, metadatas, distances):
                    # 類似度しきい値でフィルタリング
                    similarity = 1 - distance
                    if similarity >= self.config["similarity_threshold"]:
                        memory = metadata.copy()
                        memory["content"] = doc
                        memory["similarity"] = similarity
                        memories.append(memory)

            logger.debug(f"Found {len(memories)} relevant memories")
            return memories

        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []

    async def _search_mock_db(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """モックDBでの検索（簡易的なテキストマッチング）"""
        try:
            query_lower = query.lower()
            relevant_memories = []

            for memory in self.mock_memories:
                content = memory.get("content", "").lower()

                # 簡易的な関連度計算（キーワードマッチング）
                similarity = self._calculate_text_similarity(query_lower, content)

                if similarity >= self.config["similarity_threshold"]:
                    memory_copy = memory.copy()
                    memory_copy["similarity"] = similarity
                    relevant_memories.append(memory_copy)

            # 類似度でソート
            relevant_memories.sort(key=lambda x: x["similarity"], reverse=True)

            logger.debug(f"Found {len(relevant_memories[:limit])} relevant memories (mock)")
            return relevant_memories[:limit]

        except Exception as e:
            logger.error(f"Mock DB search failed: {e}")
            return []

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """簡易的なテキスト類似度計算"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    async def store_user_preference(self, key: str, value: str) -> bool:
        """
        ユーザー設定を保存

        Args:
            key: 設定のキー
            value: 設定の値

        Returns:
            保存成功かどうか
        """
        try:
            preference_memory = {
                "content": f"ユーザー設定: {key} = {value}",
                "role": "system",
                "category": "preference",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "preference_key": key,
                    "preference_value": value,
                    "type": "user_preference"
                }
            }

            await self._store_memory_entry(preference_memory)
            logger.info(f"User preference stored: {key} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to store user preference: {e}")
            return False

    async def get_user_preferences(self) -> Dict[str, str]:
        """ユーザー設定を取得"""
        try:
            preferences = {}

            if self.chroma_client and self.collection:
                # ChromaDBから検索
                results = self.collection.query(
                    query_texts=["ユーザー設定"],
                    n_results=100,
                    where={"category": "preference"},
                    include=["documents", "metadatas"]
                )

                if results["metadatas"] and len(results["metadatas"]) > 0:
                    for metadata in results["metadatas"][0]:
                        key = metadata.get("preference_key")
                        value = metadata.get("preference_value")
                        if key and value:
                            preferences[key] = value
            else:
                # モックDBから検索
                for memory in self.mock_memories:
                    if memory.get("category") == "preference":
                        metadata = memory.get("metadata", {})
                        key = metadata.get("preference_key")
                        value = metadata.get("preference_value")
                        if key and value:
                            preferences[key] = value

            logger.debug(f"Retrieved {len(preferences)} user preferences")
            return preferences

        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}

    async def _cleanup_old_memories(self):
        """古いメモリのクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config["memory_retention_days"])
            cutoff_iso = cutoff_date.isoformat()

            deleted_count = 0

            if self.chroma_client and self.collection:
                # ChromaDBでの削除は複雑なので、今回は省略
                # 実装する場合は、古いメモリのIDを特定して削除
                pass
            else:
                # モックDBでの削除
                original_count = len(self.mock_memories)
                self.mock_memories = [
                    memory for memory in self.mock_memories
                    if memory.get("timestamp", "") >= cutoff_iso
                ]
                deleted_count = original_count - len(self.mock_memories)

                if deleted_count > 0:
                    await self._persist_mock_memories()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old memory entries")

        except Exception as e:
            logger.error(f"Failed to cleanup old memories: {e}")

    async def _persist_mock_memories(self):
        """モックメモリをファイルに保存"""
        try:
            mock_file = os.path.join(self.config["db_path"], "mock_memories.json")
            with open(mock_file, 'w', encoding='utf-8') as f:
                json.dump(self.mock_memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist mock memories: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """システム状態の取得"""
        status = {
            "initialized": self.is_initialized,
            "chromadb_available": CHROMADB_AVAILABLE,
            "encoder_available": SENTENCE_TRANSFORMERS_AVAILABLE,
            "config": self.config.copy()
        }

        try:
            if self.chroma_client and self.collection:
                status["memory_count"] = self.collection.count()
                status["storage_type"] = "chromadb"
            else:
                status["memory_count"] = len(getattr(self, "mock_memories", []))
                status["storage_type"] = "mock"

        except Exception as e:
            logger.error(f"Failed to get memory status: {e}")
            status["error"] = str(e)

        return status

    async def update_config(self, config: Dict[str, Any]):
        """設定の更新"""
        logger.info(f"Updating Personal Memory config: {config}")
        self.config.update(config)

        # 重要な設定が変更された場合は再初期化
        if any(key in config for key in ["db_path", "collection_name", "embedding_model"]):
            logger.info("Critical configuration changed, reinitializing...")
            await self.cleanup()
            await self.initialize()

    async def cleanup(self):
        """リソースのクリーンアップ"""
        logger.info("Cleaning up Personal Memory system...")

        # モックメモリの保存
        if hasattr(self, "mock_memories"):
            await self._persist_mock_memories()

        # ChromaDBのクリーンアップ
        self.chroma_client = None
        self.collection = None
        self.encoder = None

        self.is_initialized = False
        logger.info("Personal Memory system cleanup completed")
# Security Architecture

## Multi-User Session Management

このアプリケーションは、複数のユーザーが同時に利用できるように設計されています。

### セッション分離

- 各ユーザーは一意のセッションIDを持ちます（UUID v4形式）
- セッションIDはブラウザのlocalStorageに保存されます
- 全てのAPIリクエストには`X-Session-ID`ヘッダーが含まれます

### データ分離

各ユーザーのデータは完全に分離されています：

```
data/
└── sessions/
    ├── {session-id-1}/
    │   ├── gmail_token.json
    │   └── calendar_token.json
    ├── {session-id-2}/
    │   ├── gmail_token.json
    │   └── calendar_token.json
    └── ...
```

### セキュリティ対策

#### 1. セッションID検証
- UUID v4形式の厳密な検証（正規表現）
- パストラバーサル攻撃の防止
- 不正なセッションIDは400エラーで拒否

#### 2. OAuth認証
- CSRF対策：stateパラメータとセッションIDの紐付け
- リフレッシュトークン対応
- スコープの最小限化

#### 3. データ保護
- `.gitignore`で全てのトークンファイルを除外
- セッションディレクトリ全体を除外（`data/`）
- 環境変数による機密情報管理

#### 4. 安全なファイルパス生成
```python
# src/middleware/session.py
def get_data_path(self, session_id: str, filename: str) -> Path:
    """セッション専用のデータパスを安全に生成"""
    if not self.validate_session_id(session_id):
        raise ValueError("Invalid session ID")
    # Path traversal攻撃を防止
    return self.base_path / session_id / f"{filename}.json"
```

## 推奨事項

### 本番環境での改善

1. **ステート管理の永続化**
   - 現在：メモリ上の辞書（`auth_states`）
   - 推奨：Redisなどの外部ストア

2. **セッションのクリーンアップ**
   - 未使用セッションの自動削除機能を追加
   - TTL（Time To Live）の設定

3. **レート制限**
   - 認証エンドポイントへのリクエスト制限
   - セッション作成の制限

4. **HTTPS必須化**
   - 本番環境では必ずHTTPSを使用
   - セッションIDの暗号化送信

## デプロイ前チェックリスト

- [ ] 全ての`*token*.json`ファイルが除外されている
- [ ] 全ての`*credential*.json`ファイルが除外されている
- [ ] `data/`ディレクトリが除外されている
- [ ] 環境変数`APP_URL`が正しく設定されている
- [ ] Google Cloud ConsoleでリダイレクトURIが登録されている
- [ ] HTTPSが有効になっている（本番環境）

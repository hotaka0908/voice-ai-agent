# フロントエンド デバッグ手順

設定画面で「取得失敗」が表示される場合、以下の手順で問題を特定してください。

## 1. ブラウザキャッシュのクリア

**重要**: まず、ブラウザのキャッシュをクリアしてください。

### Chrome/Edge
1. `Cmd+Shift+Delete` (Mac) または `Ctrl+Shift+Delete` (Windows)
2. 「キャッシュされた画像とファイル」にチェック
3. 「データを削除」をクリック
4. ページをリロード (`Cmd+R` または `Ctrl+R`)

### Safari
1. `Cmd+Option+E` でキャッシュを空にする
2. ページをリロード

## 2. ハードリロード

キャッシュを無視してリロード:
- **Mac**: `Cmd+Shift+R`
- **Windows**: `Ctrl+Shift+R`

## 3. ブラウザコンソールを確認

1. **開発者ツールを開く**:
   - Mac: `Cmd+Option+I`
   - Windows: `Ctrl+Shift+I` または `F12`

2. **Console**タブを選択

3. **確認すべきログ**:
   ```
   ✅ 正常な場合:
   🔐 Initializing Session Manager...
   ✅ Session ID: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx

   ❌ エラーの場合:
   - "window.sessionManager is not defined"
   - "Failed to fetch"
   - その他のエラーメッセージ
   ```

4. **エラーがある場合**:
   - エラーメッセージをスクリーンショットで送ってください
   - または、エラーメッセージをコピーして共有してください

## 4. Network タブを確認

1. 開発者ツールの **Network** タブを選択
2. ページをリロード
3. 以下のリクエストを確認:

   ```
   ✅ 成功すべきリクエスト:
   - /static/js/session.js (Status: 200)
   - /api/voice/current (Status: 200)
   - /api/personality (Status: 200)
   - /api/mode/current (Status: 200)
   - /api/tools (Status: 200)

   Gmail関連（未連携の場合は正常）:
   - /api/gmail/status (Status: 200, Response: {"connected": false})
   ```

4. **失敗しているリクエストがある場合**:
   - リクエストをクリック
   - Response タブでエラー内容を確認
   - スクリーンショットを共有

## 5. セッションIDの確認

ブラウザコンソールで以下を実行:

```javascript
// セッションマネージャーが存在するか確認
console.log('SessionManager exists:', typeof window.sessionManager);

// セッションIDを確認
console.log('Session ID:', localStorage.getItem('voiceagent_session_id'));

// 手動でセッションIDをリセット
localStorage.removeItem('voiceagent_session_id');
location.reload();
```

## 6. Gmailの「未連携」表示について

**これは正常な動作です！**

Gmail連携していない状態では:
- ✅ `{"connected": false, "email": null}` → 正常
- 設定画面で「未連携」と表示される → 正常
- 「連携する」ボタンが表示される → 正常

## 7. よくある問題と解決策

### 問題: 全ての設定が「取得失敗」
**原因**: キャッシュの問題、またはJavaScriptエラー
**解決策**:
1. ブラウザキャッシュをクリア
2. ハードリロード
3. それでもダメなら、コンソールのエラーを確認

### 問題: "window.sessionManager is not defined"
**原因**: session.jsが読み込まれていない
**解決策**:
1. ブラウザキャッシュをクリア
2. `/static/js/session.js` に直接アクセスして内容を確認
3. サーバーを再起動

### 問題: "Invalid session ID format"
**原因**: 古いセッションIDがLocalStorageに残っている
**解決策**:
```javascript
localStorage.removeItem('voiceagent_session_id');
location.reload();
```

## 8. デバッグ情報の収集

問題が解決しない場合、以下の情報を共有してください:

1. **ブラウザとバージョン** (例: Chrome 120, Safari 17)
2. **コンソールのエラーログ** (スクリーンショット可)
3. **Networkタブの失敗リクエスト** (スクリーンショット可)
4. **設定画面のスクリーンショット**

---

## 補足: 正常な動作

設定画面を開いたとき、以下のように表示されるのが正常です:

### Gmail未連携の場合
- ツール一覧に「Gmail」が表示される
- ステータス: 「未連携」
- Gmailをクリックすると「連携する」ボタンが表示される

### その他の設定
- **性格タイプ**: 分析結果が表示される（例: 探究的タイプ）
- **モード**: 現在のモードが表示される
- **ボイス**: 現在のボイス設定が表示される
- **ツール一覧**: 利用可能なツールが表示される

もし上記が全て「取得失敗」と表示される場合は、JavaScriptエラーまたはサーバー接続の問題です。

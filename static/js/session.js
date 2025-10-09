// Session Manager - セッション管理

class SessionManager {
    constructor() {
        this.sessionId = null;
        this.init();
    }

    init() {
        console.log('🔐 Initializing Session Manager...');
        this.sessionId = this.getOrCreateSessionId();
        console.log('✅ Session ID:', this.sessionId);
    }

    /**
     * セッションIDを取得または生成
     */
    getOrCreateSessionId() {
        // LocalStorageからセッションIDを取得
        let sessionId = localStorage.getItem('voiceagent_session_id');

        if (!sessionId) {
            // 新規セッションID生成（UUID v4）
            sessionId = this.generateUUID();
            localStorage.setItem('voiceagent_session_id', sessionId);
            console.log('🆕 New session created:', sessionId);
        } else {
            console.log('♻️  Existing session restored:', sessionId);
        }

        return sessionId;
    }

    /**
     * UUID v4を生成
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * 現在のセッションIDを取得
     */
    getSessionId() {
        return this.sessionId;
    }

    /**
     * セッションをクリア（デバッグ用）
     */
    clearSession() {
        localStorage.removeItem('voiceagent_session_id');
        this.sessionId = null;
        console.log('🗑️  Session cleared');
    }

    /**
     * セッションIDをHTTPヘッダーに追加
     */
    getHeaders() {
        return {
            'X-Session-ID': this.sessionId
        };
    }
}

// グローバルインスタンスを作成
if (typeof window !== 'undefined') {
    window.sessionManager = new SessionManager();
}

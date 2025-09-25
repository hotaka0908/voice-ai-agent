// Voice AI Agent - メインアプリケーション

class VoiceAgent {
    constructor() {
        this.isInitialized = false;
        this.isRecording = false;
        this.isSpeaking = false;
        this.audioManager = new AudioManager();
        this.websocketManager = new WebSocketManager();
        this.uiManager = new UIManager();

        this.init();
    }

    async init() {
        try {
            console.log('Initializing Voice Agent...');

            // UIの初期化
            await this.uiManager.init();

            // オーディオの初期化
            await this.audioManager.init();

            // WebSocketの初期化
            await this.websocketManager.init();

            // イベントリスナーの設定
            this.setupEventListeners();

            this.isInitialized = true;
            this.uiManager.setStatus('ready', 'システム準備完了');
            console.log('Voice Agent initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Voice Agent:', error);
            this.uiManager.setStatus('error', 'システム初期化エラー');
            this.uiManager.showError('システムの初期化に失敗しました: ' + error.message);
        }
    }

    setupEventListeners() {
        // マイクボタン
        document.getElementById('micButton').addEventListener('click', () => {
            this.toggleRecording();
        });

        // スピーカーボタン
        document.getElementById('speakerButton').addEventListener('click', () => {
            this.toggleSpeaker();
        });

        // テキスト送信ボタン
        document.getElementById('sendButton').addEventListener('click', () => {
            this.sendTextMessage();
        });

        // テキスト入力でEnterキー
        document.getElementById('textInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendTextMessage();
            }
        });

        // 設定ボタン
        document.getElementById('settingsButton').addEventListener('click', () => {
            this.uiManager.toggleSettings();
        });

        // 会話リセットボタン
        document.getElementById('resetConversation').addEventListener('click', () => {
            this.resetConversation();
        });

        // デバッグモード切り替え
        document.getElementById('debugMode').addEventListener('change', (e) => {
            this.toggleDebugMode(e.target.checked);
        });

        // 各種設定の変更
        this.setupSettingsListeners();

        // WebSocketイベント
        this.websocketManager.on('message', (data) => {
            this.handleWebSocketMessage(data);
        });

        this.websocketManager.on('connect', () => {
            this.uiManager.setConnectionStatus('connected');
        });

        this.websocketManager.on('disconnect', () => {
            this.uiManager.setConnectionStatus('disconnected');
        });

        this.websocketManager.on('error', (error) => {
            this.uiManager.setConnectionStatus('error');
            console.error('WebSocket error:', error);
        });

        // キーボードショートカット
        document.addEventListener('keydown', (e) => {
            // スペースキーで録音開始/停止
            if (e.code === 'Space' && !e.target.matches('input, textarea')) {
                e.preventDefault();
                this.toggleRecording();
            }
        });
    }

    setupSettingsListeners() {
        // STTプロバイダー変更
        document.getElementById('sttProvider').addEventListener('change', (e) => {
            this.updateSetting('stt_provider', e.target.value);
        });

        // TTSプロバイダー変更
        document.getElementById('ttsProvider').addEventListener('change', (e) => {
            this.updateSetting('tts_provider', e.target.value);
        });

        // LLMプロバイダー変更
        document.getElementById('llmProvider').addEventListener('change', (e) => {
            this.updateSetting('llm_provider', e.target.value);
        });

        // 音声感度変更
        document.getElementById('sensitivity').addEventListener('input', (e) => {
            document.getElementById('sensitivityValue').textContent = e.target.value;
            this.updateSetting('sensitivity', parseInt(e.target.value));
        });
    }

    async toggleRecording() {
        if (!this.isInitialized) {
            this.uiManager.showError('システムが初期化されていません');
            return;
        }

        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            console.log('Starting recording...');

            this.isRecording = true;
            this.uiManager.setRecordingState(true);
            this.uiManager.setStatus('recording', '聞いています...');

            await this.audioManager.startRecording();

            // 音声データのストリーミング開始
            this.audioManager.on('audioData', (audioData) => {
                this.websocketManager.sendAudioData(audioData);
            });

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.isRecording = false;
            this.uiManager.setRecordingState(false);
            this.uiManager.showError('録音を開始できませんでした: ' + error.message);
        }
    }

    async stopRecording() {
        try {
            console.log('Stopping recording...');

            await this.audioManager.stopRecording();

            this.isRecording = false;
            this.uiManager.setRecordingState(false);
            this.uiManager.setStatus('processing', '処理中...');

        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.uiManager.showError('録音を停止できませんでした: ' + error.message);
        }
    }

    toggleSpeaker() {
        const isMuted = this.audioManager.toggleMute();
        this.uiManager.setSpeakerState(!isMuted);
    }

    async sendTextMessage() {
        const textInput = document.getElementById('textInput');
        const text = textInput.value.trim();

        if (!text) return;

        try {
            // UIに送信メッセージを表示
            this.uiManager.addMessage('user', text);

            // テキストをクリア
            textInput.value = '';

            // WebSocketでテキストを送信
            await this.websocketManager.sendTextMessage(text);

            this.uiManager.setStatus('processing', '処理中...');

        } catch (error) {
            console.error('Failed to send text message:', error);
            this.uiManager.showError('メッセージの送信に失敗しました: ' + error.message);
        }
    }

    handleWebSocketMessage(data) {
        console.log('Received WebSocket message:', data);

        switch (data.type) {
            case 'response':
                this.handleResponse(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            case 'status':
                this.handleStatus(data);
                break;
            case 'audio':
                this.handleAudioResponse(data);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    async handleResponse(data) {
        try {
            // テキスト応答を表示
            if (data.content) {
                this.uiManager.addMessage('assistant', data.content);
            }

            // 音声があれば再生
            if (data.audio_url) {
                await this.playAudioResponse(data.audio_url);
            }

            // ツール実行結果の表示
            if (data.tool_results && data.tool_results.length > 0) {
                this.displayToolResults(data.tool_results);
            }

            this.uiManager.setStatus('ready', 'システム準備完了');

        } catch (error) {
            console.error('Failed to handle response:', error);
            this.uiManager.showError('応答の処理に失敗しました');
        }
    }

    handleError(data) {
        console.error('Server error:', data.message);
        this.uiManager.showError(data.message || 'サーバーエラーが発生しました');
        this.uiManager.setStatus('error', 'エラー');
    }

    handleStatus(data) {
        this.uiManager.setSystemStatus(data.status);
    }

    async handleAudioResponse(data) {
        try {
            // Base64音声データをデコードして再生
            const audioBlob = this.base64ToBlob(data.audio, 'audio/wav');
            const audioUrl = URL.createObjectURL(audioBlob);
            await this.playAudioResponse(audioUrl);
        } catch (error) {
            console.error('Failed to handle audio response:', error);
        }
    }

    async playAudioResponse(audioUrl) {
        try {
            this.isSpeaking = true;
            this.uiManager.setSpeakingState(true);

            await this.audioManager.playAudio(audioUrl);

            this.isSpeaking = false;
            this.uiManager.setSpeakingState(false);
        } catch (error) {
            console.error('Failed to play audio:', error);
            this.isSpeaking = false;
            this.uiManager.setSpeakingState(false);
        }
    }

    displayToolResults(toolResults) {
        for (const tool of toolResults) {
            this.uiManager.addToolResult(tool.name, tool.result);
        }
    }

    async updateSetting(key, value) {
        try {
            const config = { [key]: value };
            await this.websocketManager.updateConfig(config);
            console.log('Setting updated:', key, value);
        } catch (error) {
            console.error('Failed to update setting:', error);
        }
    }

    toggleDebugMode(enabled) {
        if (enabled) {
            document.getElementById('textInputArea').style.display = 'flex';
            console.log('Debug mode enabled');
        } else {
            document.getElementById('textInputArea').style.display = 'none';
            console.log('Debug mode disabled');
        }
    }

    async resetConversation() {
        if (confirm('会話履歴をリセットしますか？')) {
            try {
                await this.websocketManager.resetConversation();
                this.uiManager.clearConversation();
                this.uiManager.addMessage('assistant', 'こんにちは！会話をリセットしました。何かお手伝いできることはありますか？');
            } catch (error) {
                console.error('Failed to reset conversation:', error);
                this.uiManager.showError('会話のリセットに失敗しました');
            }
        }
    }

    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }
}

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
    window.voiceAgent = new VoiceAgent();
});

// エラーハンドリング
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    if (window.voiceAgent && window.voiceAgent.uiManager) {
        window.voiceAgent.uiManager.showError('予期しないエラーが発生しました');
    }
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    if (window.voiceAgent && window.voiceAgent.uiManager) {
        window.voiceAgent.uiManager.showError('システムエラーが発生しました');
    }
});
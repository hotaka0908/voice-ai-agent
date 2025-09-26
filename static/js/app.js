// Voice AI Agent - メインアプリケーション

class VoiceAgent {
    constructor() {
        this.isInitialized = false;
        this.isRecording = false;
        this.isSpeaking = false;
        this.micActive = false; // 連続リスニングの意図フラグ
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

        // 音声からのメッセージ処理
        this.websocketManager.on('voiceMessage', (data) => {
            console.log('🎵 voiceMessage event received in app.js:', data);
            this.handleVoiceMessage(data);
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

        // 個人情報保存ボタン
        document.getElementById('savePersonalInfo').addEventListener('click', () => {
            this.savePersonalInfo();
        });

        // 設定パネル閉じるボタン
        document.getElementById('closeSettingsButton').addEventListener('click', () => {
            this.uiManager.closeSettings();
        });
    }

    async toggleRecording() {
        if (!this.isInitialized) {
            this.uiManager.showError('システムが初期化されていません');
            return;
        }

        if (this.micActive) {
            // 連続リスニング停止
            this.micActive = false;
            await this.stopRecording();
        } else {
            // 連続リスニング開始
            this.micActive = true;
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

        // 録音状態イベント
        this.audioManager.on('recordingStart', () => {
            this.isRecording = true;
            this.uiManager.setRecordingState(true);
        });
        this.audioManager.on('recordingStop', () => {
            this.isRecording = false;
            this.uiManager.setRecordingState(false);
            // 連続リスニングが有効なら自動再開
            if (this.micActive) {
                this.startRecording();
            }
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
            case 'user_message':
            case 'assistant_message':
                // 音声メッセージは専用ハンドラーに転送
                console.log('🎯 Forwarding voice message to handleVoiceMessage:', data.type);
                this.handleVoiceMessage(data);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    handleVoiceMessage(data) {
        console.log('🎯 APP handleVoiceMessage called with:', data);
        console.log('🎯 Message type:', data.type);
        console.log('🎯 Message content:', data.content);

        switch (data.type) {
            case 'user_message':
                console.log('👤 Processing user message:', data.content);
                // ユーザーの音声認識結果をチャット欄に表示
                this.uiManager.addMessage('user', data.content, data.timestamp);
                console.log('👤 User message added to UI');
                break;
            case 'assistant_message':
                console.log('🤖 Processing assistant message:', data.content);
                // AIの応答をチャット欄に表示
                this.uiManager.addMessage('assistant', data.content, data.timestamp);
                console.log('🤖 Assistant message added to UI');

                // 音声がある場合は再生
                if (data.audio_url) {
                    console.log('🔊 Playing audio:', data.audio_url);
                    console.log('🔊 About to call playAudioResponse...');
                    this.playAudioResponse(data.audio_url)
                        .then(() => console.log('🔊 playAudioResponse promise resolved'))
                        .catch(err => console.error('🔊 playAudioResponse promise rejected:', err));
                } else {
                    console.log('⚠️ No audio_url in assistant message');
                }
                break;
            default:
                console.warn('❓ Unknown voice message type:', data.type);
        }

        // 処理中状態をリセット
        console.log('✅ Resetting processing state');
        this.uiManager.setStatus('ready', 'システム準備完了');
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
            console.log('🔊 APP playAudioResponse called with:', audioUrl);
            this.isSpeaking = true;
            this.uiManager.setSpeakingState(true);

            console.log('🔊 Calling audioManager.playAudio...');
            await this.audioManager.playAudio(audioUrl);
            console.log('🔊 audioManager.playAudio completed');

            this.isSpeaking = false;
            this.uiManager.setSpeakingState(false);
        } catch (error) {
            console.error('❌ Failed to play audio:', error);
            console.error('❌ Error details:', error.stack);
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

    async savePersonalInfo() {
        try {
            console.log('Saving personal information...');

            // 個人情報フォームの値を取得
            const personalInfo = {
                name: document.getElementById('userName').value.trim(),
                age: parseInt(document.getElementById('userAge').value) || null,
                location: document.getElementById('userLocation').value.trim(),
                occupation: document.getElementById('userOccupation').value.trim(),
                hobbies: document.getElementById('userHobbies').value.trim()
            };

            // 空の値をフィルタリング
            const filteredInfo = Object.fromEntries(
                Object.entries(personalInfo).filter(([key, value]) =>
                    value !== null && value !== ''
                )
            );

            if (Object.keys(filteredInfo).length === 0) {
                this.uiManager.showError('保存する情報を入力してください');
                return;
            }

            // WebSocket経由で個人情報を保存
            await this.websocketManager.savePersonalInfo(filteredInfo);

            this.uiManager.showSuccess('個人情報を保存しました');
            console.log('Personal information saved:', filteredInfo);

        } catch (error) {
            console.error('Failed to save personal information:', error);
            this.uiManager.showError('個人情報の保存に失敗しました: ' + error.message);
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

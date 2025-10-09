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
        this.alarms = []; // アラーム一覧
        this.alarmTimers = []; // アラームタイマー
        this.tableTasks = []; // テーブルタスク一覧

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

            // 初期ボイス設定を読み込んで画像を設定
            await this.loadCurrentVoice();

            // アラームの読み込みとスケジュール
            await this.loadAndScheduleAlarms();

            this.isInitialized = true;
            this.uiManager.setStatus('ready', '話しかけてね');
            console.log('Voice Agent initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Voice Agent:', error);
            this.uiManager.setStatus('error', 'システム初期化エラー');
            this.uiManager.showError('システムの初期化に失敗しました: ' + error.message);
        }
    }

    setupEventListeners() {
        // 画像コンテナクリックで音声入力
        document.querySelector('.image-container').addEventListener('click', () => {
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

            // 設定が開かれたときに各種情報をロード
            if (this.uiManager.isSettingsOpen) {
                setTimeout(() => {
                    this.loadPersonalityType();
                    this.loadCurrentMode();
                    this.loadCurrentLLMConfig();
                    this.loadCurrentVoice();
                    this.loadAvailableTools();
                    this.loadTableTasks();
                }, 300);
            }
        });


        // 各種設定の変更
        this.setupSettingsListeners();

        // AudioManagerのイベントリスナーを一度だけ登録
        this.setupAudioListeners();

        // 連絡先ボタンのイベントリスナー
        this.setupContactListeners();

        // WebSocketイベント
        this.websocketManager.on('message', (data) => {
            this.handleWebSocketMessage(data);
        });

        // 音声からのメッセージ処理
        this.websocketManager.on('voiceMessage', (data) => {
            console.log('🎵 voiceMessage event received in app.js:', data);
            this.handleVoiceMessage(data);
        });

        // ステータス更新処理
        this.websocketManager.on('status', (data) => {
            console.log('📊 Status event received:', data);
            this.showProcessingStatus(data.message);
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

        // アラームダイアログのイベントリスナー
        this.setupAlarmListeners();

        // Gmailダイアログのイベントリスナー
        this.setupGmailListeners();
        this.setupCalendarListeners();
    }

    setupAudioListeners() {
        // AudioManagerのイベントリスナーを1回だけ登録
        this.audioManager.on('audioData', (audioData) => {
            this.uiManager.setProcessingState(true);
            this.websocketManager.sendAudioData(audioData);
        });

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
    }

    setupSettingsListeners() {
        // 個人情報保存ボタン
        document.getElementById('savePersonalInfo').addEventListener('click', () => {
            this.savePersonalInfo();
        });

        // 設定パネル閉じるボタン
        document.getElementById('closeSettingsButton').addEventListener('click', () => {
            this.uiManager.closeSettings();
        });

        // 性格タイプ更新ボタン
        document.getElementById('refreshPersonality').addEventListener('click', () => {
            this.loadPersonalityType();
        });

        // モード設定適用ボタン
        document.getElementById('applyModeSettings').addEventListener('click', () => {
            this.applyModeSettings();
        });

        // LLM設定適用ボタン
        document.getElementById('applyLLMSettings').addEventListener('click', () => {
            this.applyLLMSettings();
        });

        // ボイス設定適用ボタン
        document.getElementById('applyVoiceSettings').addEventListener('click', () => {
            this.applyVoiceSettings();
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

    setupContactListeners() {
        // 全ての連絡先ボタンにイベントリスナーを追加
        document.querySelectorAll('.contact-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const contactItem = e.target.closest('.contact-item');
                const contactName = contactItem.querySelector('.contact-name').textContent;
                const isPhoneBtn = e.target.classList.contains('phone-btn');

                if (isPhoneBtn) {
                    this.handlePhoneCall(contactName);
                } else {
                    this.handleVoiceMessage(contactName);
                }
            });
        });
    }

    handlePhoneCall(contactName) {
        alert(`${contactName}への電話機能は準備中です`);
    }

    handleVoiceMessage(contactName) {
        alert(`${contactName}へのボイスメッセージ機能は準備中です`);
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

    showProcessingStatus(message) {
        console.log('📊 Showing processing status:', message);
        const statusDiv = document.getElementById('processing-status');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.style.display = 'block';

            // 完了メッセージの場合は自動的に非表示
            if (message.includes('完了') || message.includes('✅')) {
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 2000);
            }
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

            this.uiManager.setStatus('ready', '話しかけてね');

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

            // 処理中状態を解除
            this.uiManager.setProcessingState(false);

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
            // エラー時も処理中状態を解除
            this.uiManager.setProcessingState(false);
        }
    }

    displayToolResults(toolResults) {
        for (const tool of toolResults) {
            this.uiManager.addToolResult(tool.name, tool.result);

            // アラームツールの場合、フロントエンドのスケジューラーに登録
            if (tool.name === 'alarm' && tool.result && tool.result.alarm) {
                const alarm = tool.result.alarm;
                console.log('🔔 Scheduling alarm from AI tool result:', alarm);

                // アラーム配列に追加
                this.alarms.push(alarm);

                // スケジュールに登録
                this.scheduleAlarm(alarm);

                // アラーム一覧を更新
                this.loadAlarmList();
            }
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

    async loadPersonalityType() {
        try {
            console.log('Loading personality type...');

            const card = document.getElementById('personalityCard');
            if (!card) return;

            // ローディング状態を表示
            card.innerHTML = `
                <div class="personality-loading">
                    <div class="spinner"></div>
                    <p>分析中...</p>
                </div>
            `;

            // APIから性格タイプを取得
            const response = await fetch('/api/personality');
            const data = await response.json();

            console.log('Personality type data:', data);

            // 性格タイプを表示
            this.displayPersonalityType(data);

        } catch (error) {
            console.error('Failed to load personality type:', error);
            const card = document.getElementById('personalityCard');
            if (card) {
                card.innerHTML = `
                    <div class="personality-error">
                        <p>⚠️ 性格タイプの取得に失敗しました</p>
                        <button onclick="window.voiceAgent.loadPersonalityType()" class="retry-btn">再試行</button>
                    </div>
                `;
            }
        }
    }

    async loadCurrentMode() {
        try {
            console.log('Loading current mode...');

            const response = await fetch('/api/mode/current');
            const data = await response.json();

            console.log('Current mode:', data);

            // モードを設定
            if (data.mode) {
                document.getElementById('aiMode').value = data.mode;
            }

            // 現在のモード情報を表示
            const modeNames = {
                'assist': 'スタンダードモード',
                'auto': '全自動モード'
            };
            const modeName = modeNames[data.mode] || data.mode;
            document.getElementById('currentModeValue').textContent = modeName;

        } catch (error) {
            console.error('Failed to load current mode:', error);
            document.getElementById('currentModeValue').textContent = '取得失敗';
        }
    }

    async applyModeSettings() {
        try {
            console.log('Applying mode settings...');

            const mode = document.getElementById('aiMode').value;

            if (!mode) {
                this.uiManager.showError('モードを選択してください');
                return;
            }

            // APIでモードを切り替え
            const response = await fetch('/api/mode/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ mode })
            });

            const result = await response.json();

            if (result.error) {
                this.uiManager.showError(`モード切り替え失敗: ${result.error}`);
                return;
            }

            const modeNames = {
                'assist': 'スタンダードモード',
                'auto': '全自動モード'
            };
            const modeName = modeNames[mode];
            this.uiManager.showSuccess(`${modeName}に切り替えました`);
            console.log('Mode settings applied:', result);

            // 現在のモード情報を更新
            await this.loadCurrentMode();

        } catch (error) {
            console.error('Failed to apply mode settings:', error);
            this.uiManager.showError('モードの切り替えに失敗しました: ' + error.message);
        }
    }

    displayPersonalityType(data) {
        const card = document.getElementById('personalityCard');
        if (!card) return;

        const confidence = data.confidence || 0;
        const confidenceColor = confidence >= 70 ? '#10b981' : confidence >= 40 ? '#f59e0b' : '#6b7280';

        // 分析データの表示
        let analysisDataHtml = '';
        if (data.analysis_data) {
            const ad = data.analysis_data;
            analysisDataHtml = `
                <div class="analysis-data">
                    <h5 style="font-size: 0.9rem; margin: 1rem 0 0.5rem 0; color: #64748b;">📊 分析データ</h5>
                    <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem;">
                        <div>総メッセージ数: ${ad.message_count || 0}件</div>
                        <div>会話履歴: ${ad.data_sources?.conversations || 0}件</div>
                        <div>個人情報: ${ad.data_sources?.personal_info || 0}件</div>
                    </div>
                    ${ad.trait_scores ? `
                        <div style="margin-top: 0.8rem;">
                            <h6 style="font-size: 0.85rem; margin-bottom: 0.4rem; color: #64748b;">特性スコア:</h6>
                            ${Object.entries(ad.trait_scores).map(([trait, score]) => `
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                                    <span style="font-size: 0.8rem; color: #475569;">${trait}</span>
                                    <div style="flex: 1; margin: 0 0.5rem; background: #e2e8f0; height: 6px; border-radius: 3px; overflow: hidden;">
                                        <div style="width: ${Math.min(100, score * 10)}%; height: 100%; background: #3b82f6;"></div>
                                    </div>
                                    <span style="font-size: 0.75rem; color: #94a3b8; min-width: 30px; text-align: right;">${score}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        card.innerHTML = `
            <div class="personality-content">
                <div class="personality-icon">${data.icon || '❓'}</div>
                <h4 class="personality-type">${data.type || '未分析'}</h4>
                <p class="personality-description">${data.description || ''}</p>

                ${data.traits && data.traits.length > 0 ? `
                    <div class="personality-traits">
                        ${data.traits.map(trait => `<span class="trait-badge">${trait}</span>`).join('')}
                    </div>
                ` : ''}

                ${confidence > 0 ? `
                    <div class="confidence-bar">
                        <div class="confidence-label">
                            <span>信頼度</span>
                            <span class="confidence-value">${confidence}%</span>
                        </div>
                        <div class="confidence-track">
                            <div class="confidence-fill" style="width: ${confidence}%; background-color: ${confidenceColor};"></div>
                        </div>
                    </div>
                ` : ''}

                ${analysisDataHtml}
            </div>
        `;
    }

    async loadCurrentLLMConfig() {
        try {
            console.log('Loading current LLM config...');

            const response = await fetch('/api/llm/current');
            const data = await response.json();

            console.log('Current LLM config:', data);

            // プロバイダーを設定
            if (data.provider) {
                document.getElementById('llmProvider').value = data.provider;
            }

            // 現在のプロバイダー情報を表示
            const providerName = data.provider === 'claude' ? 'Claude' : data.provider === 'openai' ? 'ChatGPT' : data.provider;
            document.getElementById('currentModelValue').textContent = providerName;

        } catch (error) {
            console.error('Failed to load current LLM config:', error);
            document.getElementById('currentModelValue').textContent = '取得失敗';
        }
    }

    async applyLLMSettings() {
        try {
            console.log('Applying LLM settings...');

            const provider = document.getElementById('llmProvider').value;

            if (!provider) {
                this.uiManager.showError('プロバイダーを選択してください');
                return;
            }

            // デフォルトモデルを設定
            const defaultModels = {
                'claude': 'claude-3-haiku-20240307',
                'openai': 'gpt-4o-mini'
            };

            const model = defaultModels[provider];

            // APIでプロバイダーを切り替え
            const response = await fetch('/api/llm/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ provider, model })
            });

            const result = await response.json();

            if (result.error) {
                this.uiManager.showError(`プロバイダー切り替え失敗: ${result.error}`);
                return;
            }

            const providerName = provider === 'claude' ? 'Claude' : 'ChatGPT';
            this.uiManager.showSuccess(`${providerName}に切り替えました`);
            console.log('LLM settings applied:', result);

            // 現在のプロバイダー情報を更新
            await this.loadCurrentLLMConfig();

        } catch (error) {
            console.error('Failed to apply LLM settings:', error);
            this.uiManager.showError('プロバイダーの切り替えに失敗しました: ' + error.message);
        }
    }

    async loadCurrentVoice() {
        try {
            console.log('Loading current voice...');

            const response = await fetch('/api/voice/current');
            const data = await response.json();

            console.log('Current voice:', data);

            // ボイスを設定
            if (data.voice) {
                document.getElementById('voiceSelect').value = data.voice;
                // 画像を更新
                this.updateAgentImage(data.voice);
            }

            // 現在のボイス情報を表示
            const voiceNames = {
                'alloy': '女性',
                'echo': '男性',
                'fable': '五条悟',
                'shimmer': '初音ミク',
                'nova': 'Nova (女性・明るい)',
                'onyx': 'Onyx (男性・深い)'
            };
            const voiceName = voiceNames[data.voice] || data.voice;
            document.getElementById('currentVoiceValue').textContent = voiceName;

        } catch (error) {
            console.error('Failed to load current voice:', error);
            document.getElementById('currentVoiceValue').textContent = '取得失敗';
        }
    }

    async applyVoiceSettings() {
        try {
            console.log('Applying voice settings...');

            const voice = document.getElementById('voiceSelect').value;

            if (!voice) {
                this.uiManager.showError('ボイスを選択してください');
                return;
            }

            // APIでボイスを切り替え
            const response = await fetch('/api/voice/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ voice })
            });

            const result = await response.json();

            if (result.error) {
                this.uiManager.showError(`ボイス切り替え失敗: ${result.error}`);
                return;
            }

            const voiceNames = {
                'alloy': '女性',
                'echo': '男性',
                'fable': '五条悟',
                'shimmer': '初音ミク',
                'onyx': 'Onyx',
                'nova': 'Nova'
            };
            const voiceName = voiceNames[voice] || voice;
            this.uiManager.showSuccess(`${voiceName}に切り替えました`);
            console.log('Voice settings applied:', result);

            // 画像を更新
            this.updateAgentImage(voice);

            // 現在のボイス情報を更新
            await this.loadCurrentVoice();

        } catch (error) {
            console.error('Failed to apply voice settings:', error);
            this.uiManager.showError('ボイスの切り替えに失敗しました: ' + error.message);
        }
    }

    async loadAvailableTools() {
        try {
            console.log('🔧 Loading available tools...');

            const listContainer = document.getElementById('toolsList');
            if (!listContainer) {
                console.error('❌ toolsList element not found');
                return;
            }

            // ローディング状態を表示
            listContainer.innerHTML = `
                <div class="tools-loading">
                    <div class="spinner"></div>
                    <p>読み込み中...</p>
                </div>
            `;

            // APIからツール一覧を取得
            console.log('🔧 Fetching from /api/tools...');
            const response = await fetch('/api/tools');
            console.log('🔧 Response status:', response.status);

            const data = await response.json();
            console.log('🔧 Available tools data:', data);

            // 除外するツール
            const excludedTools = ['time', 'calculator', 'weather', 'search', 'mobile_bridge', 'memory', 'mcp'];

            // フィルタリング
            const filteredTools = data.tools.filter(tool => !excludedTools.includes(tool.name));

            // ツール一覧を表示
            if (filteredTools && filteredTools.length > 0) {
                listContainer.innerHTML = filteredTools.map(tool => {
                    const isConnected = this.isToolConnected(tool.name);
                    const statusText = isConnected ? '連携済み' : '未連携';
                    const statusClass = isConnected ? 'connected' : 'not-connected';

                    return `
                        <div class="tool-item" data-tool-name="${tool.name}">
                            <div class="tool-info">
                                <div class="tool-name">${this.getToolDisplayName(tool.name)}</div>
                                <div class="tool-description">${tool.description}</div>
                            </div>
                            <div class="tool-status ${statusClass}">
                                ${statusText}
                            </div>
                        </div>
                    `;
                }).join('');

                // ツールアイテムにクリックイベントを追加
                document.querySelectorAll('.tool-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const toolName = item.getAttribute('data-tool-name');
                        this.handleToolClick(toolName);
                    });
                });
            } else {
                listContainer.innerHTML = `
                    <div class="tools-empty">
                        <p>利用可能なツールがありません</p>
                    </div>
                `;
            }

        } catch (error) {
            console.error('Failed to load available tools:', error);
            const listContainer = document.getElementById('toolsList');
            if (listContainer) {
                listContainer.innerHTML = `
                    <div class="tools-error">
                        <p>⚠️ ツール一覧の取得に失敗しました</p>
                    </div>
                `;
            }
        }
    }

    getToolIcon(toolName) {
        const icons = {
            'time': '⏰',
            'calculator': '🧮',
            'memory': '🧠',
            'weather': '🌤️',
            'search': '🔍',
            'mobile_bridge': '📱',
            'mcp': '🔌',
            'gmail': '📧',
            'calendar': '📅',
            'alarm': '⏰',
            'vision': '👁️',
            'aircon': '❄️',
            'light': '💡',
            'taxi': '🚕',
            'robot': '🤖'
        };
        return icons[toolName] || '🔧';
    }

    getToolDisplayName(toolName) {
        const names = {
            'time': '時刻',
            'calculator': '計算機',
            'memory': 'メモリ',
            'weather': '天気',
            'search': '検索',
            'mobile_bridge': 'モバイル連携',
            'mcp': 'MCP',
            'gmail': 'Gmail & Calendar',
            'calendar': 'カレンダー',
            'alarm': 'アラーム',
            'vision': 'ビジョン',
            'aircon': 'エアコン',
            'light': '電気(リビング)',
            'taxi': 'タクシー',
            'robot': 'ロボット'
        };
        return names[toolName] || toolName;
    }

    isToolConnected(toolName) {
        // 連携済みのツールを定義
        const connectedTools = ['gmail', 'calendar', 'alarm', 'vision'];
        return connectedTools.includes(toolName);
    }

    handleToolClick(toolName) {
        console.log('🔧 Tool clicked:', toolName);

        if (toolName === 'alarm') {
            this.openAlarmDialog();
        } else if (toolName === 'calendar') {
            this.showCalendarInfo();
        } else if (toolName === 'gmail') {
            this.showGmailInfo();
        }
    }

    async showGmailInfo() {
        // ダイアログを開く
        document.getElementById('gmailDialog').style.display = 'flex';

        try {
            console.log('📧 Checking Gmail & Calendar status...');

            // セッションIDを含めてリクエスト
            const headers = window.sessionManager.getHeaders();
            const response = await fetch('/api/gmail/status', { headers });

            console.log('📧 Response status:', response.status);
            const data = await response.json();
            console.log('📧 Gmail & Calendar status:', data);

            const gmailStatus = document.getElementById('gmailStatus');

            if (data.connected && data.email) {
                // 連携済み
                gmailStatus.innerHTML = `
                    <div class="gmail-connected">
                        <div class="status-icon">✅</div>
                        <h4>Gmail & Calendar連携中</h4>
                        <div class="gmail-email">
                            <label>連携アカウント:</label>
                            <p>${data.email}</p>
                        </div>
                        <p class="info-message" style="font-size: 0.9rem; color: #666; margin: 0.5rem 0;">GmailとCalendarの両方が使用可能です</p>
                        <button onclick="window.voiceAgent.disconnectGmail()" class="disconnect-btn">
                            連携解除
                        </button>
                    </div>
                `;
            } else {
                // 未連携
                gmailStatus.innerHTML = `
                    <div class="gmail-disconnected">
                        <div class="status-icon">📧📅</div>
                        <h4>Gmail & Calendar未連携</h4>
                        <p class="info-message">1度の認証でGmailとCalendarの両方が使えます</p>
                        <button onclick="window.voiceAgent.connectGmail()" class="connect-btn">
                            連携する
                        </button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to get Gmail status:', error);
            const gmailStatus = document.getElementById('gmailStatus');
            gmailStatus.innerHTML = `
                <div class="gmail-error">
                    <div class="status-icon">⚠️</div>
                    <h4>エラー</h4>
                    <p class="error-message">Gmail情報の取得に失敗しました</p>
                </div>
            `;
        }
    }

    async connectGmail() {
        try {
            console.log('🔗 Starting Gmail connection...');

            // 認証URLを取得
            const headers = window.sessionManager.getHeaders();
            const response = await fetch('/api/gmail/auth/start', { headers });

            if (!response.ok) {
                throw new Error('Failed to start Gmail authentication');
            }

            const data = await response.json();
            console.log('📧 Auth URL:', data.auth_url);

            // ポップアップで認証ページを開く
            const width = 600;
            const height = 700;
            const left = (screen.width - width) / 2;
            const top = (screen.height - height) / 2;

            const authWindow = window.open(
                data.auth_url,
                'Gmail認証',
                `width=${width},height=${height},left=${left},top=${top}`
            );

            if (!authWindow) {
                alert('ポップアップがブロックされました。ポップアップを許可してください。');
                return;
            }

            // postMessageで結果を受け取る
            window.addEventListener('message', async (event) => {
                if (event.data.type === 'gmail_auth_success') {
                    console.log('✅ Gmail連携成功！');

                    // ダイアログを更新
                    await this.showGmailInfo();

                    // ツールリストを再読み込み
                    await this.loadAvailableTools();
                }
            }, { once: true });

        } catch (error) {
            console.error('Failed to connect Gmail:', error);
            alert('Gmail連携に失敗しました: ' + error.message);
        }
    }

    async disconnectGmail() {
        if (!confirm('Gmail連携を解除しますか？')) {
            return;
        }

        try {
            console.log('🔌 Disconnecting Gmail...');

            const headers = window.sessionManager.getHeaders();
            const response = await fetch('/api/gmail/disconnect', {
                method: 'POST',
                headers
            });

            if (!response.ok) {
                throw new Error('Failed to disconnect Gmail');
            }

            const data = await response.json();
            console.log('✅ Gmail連携解除成功:', data.message);

            // ダイアログを更新
            await this.showGmailInfo();

            // ツールリストを再読み込み
            await this.loadAvailableTools();

        } catch (error) {
            console.error('Failed to disconnect Gmail:', error);
            alert('Gmail連携解除に失敗しました: ' + error.message);
        }
    }

    async showCalendarInfo() {
        // ダイアログを開く
        document.getElementById('calendarDialog').style.display = 'flex';

        try {
            console.log('📅 Fetching Calendar info from /api/calendar/info...');
            const response = await fetch('/api/calendar/info');
            console.log('📅 Response status:', response.status);
            const data = await response.json();
            console.log('📅 Calendar info data:', data);

            const calendarStatus = document.getElementById('calendarStatus');

            if (data.connected) {
                const displayEmail = data.email || (data.calendars && data.calendars.length > 0 ? data.calendars[0] : '連携済み');
                calendarStatus.innerHTML = `
                    <div class="gmail-connected">
                        <div class="status-icon">✅</div>
                        <h4>カレンダー連携中</h4>
                        <div class="gmail-email">
                            <label>連携アカウント:</label>
                            <p>${displayEmail}</p>
                        </div>
                    </div>
                `;
            } else {
                calendarStatus.innerHTML = `
                    <div class="gmail-disconnected">
                        <div class="status-icon">❌</div>
                        <h4>カレンダー未連携</h4>
                        <p class="error-message">${data.error || '認証情報が見つかりません'}</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to get Calendar info:', error);
            const calendarStatus = document.getElementById('calendarStatus');
            calendarStatus.innerHTML = `
                <div class="gmail-error">
                    <div class="status-icon">⚠️</div>
                    <h4>エラー</h4>
                    <p class="error-message">カレンダー情報の取得に失敗しました</p>
                </div>
            `;
        }
    }

    setupGmailListeners() {
        // Gmailダイアログの閉じるボタン
        document.getElementById('closeGmailDialog').addEventListener('click', () => {
            this.closeGmailDialog();
        });

        document.getElementById('closeGmailInfoBtn').addEventListener('click', () => {
            this.closeGmailDialog();
        });

        // ダイアログ外クリックで閉じる
        document.getElementById('gmailDialog').addEventListener('click', (e) => {
            if (e.target.id === 'gmailDialog') {
                this.closeGmailDialog();
            }
        });
    }

    closeGmailDialog() {
        document.getElementById('gmailDialog').style.display = 'none';
    }

    setupCalendarListeners() {
        // カレンダーダイアログの閉じるボタン
        document.getElementById('closeCalendarDialog').addEventListener('click', () => {
            this.closeCalendarDialog();
        });

        document.getElementById('closeCalendarInfoBtn').addEventListener('click', () => {
            this.closeCalendarDialog();
        });
    }

    closeCalendarDialog() {
        document.getElementById('calendarDialog').style.display = 'none';
    }

    updateAgentImage(voice) {
        const agentImage = document.getElementById('agentImage');
        if (!agentImage) {
            console.error('❌ agentImage element not found');
            return;
        }

        console.log(`🖼️ updateAgentImage called with voice: "${voice}" (type: ${typeof voice}, length: ${voice?.length})`);

        // ボイスごとに画像を設定
        const voiceImageMap = {
            'alloy': '/static/images/fishw.png',   // 女性
            'echo': '/static/images/fishm.png',    // 男性
            'fable': '/static/images/gojo.png',    // 五条悟
            'shimmer': '/static/images/miku.png.webp'  // 初音ミク
        };

        console.log(`🔍 Looking for mapping: voiceImageMap["${voice}"] = ${voiceImageMap[voice]}`);
        console.log(`🔍 Available mappings:`, Object.keys(voiceImageMap));

        if (voiceImageMap[voice]) {
            agentImage.src = voiceImageMap[voice];
            agentImage.alt = `AI Agent (${voice})`;
            console.log(`✅ Updated image to ${voiceImageMap[voice]} (${voice} voice)`);
        } else {
            console.warn(`⚠️ No image mapping found for voice: "${voice}"`);
        }
    }

    playAlarmSound() {
        // Web Audio APIを使って鈴の音を生成
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const now = audioContext.currentTime;

        // ベル音を3回鳴らす
        for (let i = 0; i < 3; i++) {
            const startTime = now + (i * 0.3);

            // 高音の正弦波（ベルの基音）
            const oscillator1 = audioContext.createOscillator();
            const gainNode1 = audioContext.createGain();
            oscillator1.connect(gainNode1);
            gainNode1.connect(audioContext.destination);

            oscillator1.frequency.setValueAtTime(880, startTime); // A5
            oscillator1.type = 'sine';

            // エンベロープ（音量の変化）
            gainNode1.gain.setValueAtTime(0, startTime);
            gainNode1.gain.linearRampToValueAtTime(0.3, startTime + 0.01);
            gainNode1.gain.exponentialRampToValueAtTime(0.01, startTime + 0.25);

            oscillator1.start(startTime);
            oscillator1.stop(startTime + 0.25);

            // 倍音を追加（よりリアルなベル音に）
            const oscillator2 = audioContext.createOscillator();
            const gainNode2 = audioContext.createGain();
            oscillator2.connect(gainNode2);
            gainNode2.connect(audioContext.destination);

            oscillator2.frequency.setValueAtTime(1320, startTime); // E6
            oscillator2.type = 'sine';

            gainNode2.gain.setValueAtTime(0, startTime);
            gainNode2.gain.linearRampToValueAtTime(0.15, startTime + 0.01);
            gainNode2.gain.exponentialRampToValueAtTime(0.01, startTime + 0.2);

            oscillator2.start(startTime);
            oscillator2.stop(startTime + 0.2);
        }

        // ベル音の再生時間（約1秒）を返す
        return new Promise(resolve => setTimeout(resolve, 1000));
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

    // ============= アラーム機能 =============

    setupAlarmListeners() {
        // 時刻入力の検証
        const hourInput = document.getElementById('alarmHour');
        const minuteInput = document.getElementById('alarmMinute');

        hourInput.addEventListener('blur', () => {
            let value = parseInt(hourInput.value) || 0;
            if (value < 0) value = 0;
            if (value > 23) value = 23;
            hourInput.value = value.toString().padStart(2, '0');
        });

        minuteInput.addEventListener('blur', () => {
            let value = parseInt(minuteInput.value) || 0;
            if (value < 0) value = 0;
            if (value > 59) value = 59;
            minuteInput.value = value.toString().padStart(2, '0');
        });

        // アラームダイアログの閉じるボタン
        document.getElementById('closeAlarmDialog').addEventListener('click', () => {
            this.closeAlarmDialog();
        });

        document.getElementById('cancelAlarmBtn').addEventListener('click', () => {
            this.closeAlarmDialog();
        });

        // アラーム設定ボタン
        document.getElementById('setAlarmBtn').addEventListener('click', () => {
            this.setAlarm();
        });

        // ダイアログ外クリックで閉じる
        document.getElementById('alarmDialog').addEventListener('click', (e) => {
            if (e.target.id === 'alarmDialog') {
                this.closeAlarmDialog();
            }
        });
    }

    openAlarmDialog() {
        document.getElementById('alarmDialog').style.display = 'flex';
        this.loadAlarmList();
    }

    closeAlarmDialog() {
        document.getElementById('alarmDialog').style.display = 'none';
        // フォームをクリア
        document.getElementById('alarmHour').value = '12';
        document.getElementById('alarmMinute').value = '00';
        document.getElementById('alarmMessage').value = '';
        document.getElementById('alarmRepeat').checked = false;
    }

    async setAlarm() {
        const hour = document.getElementById('alarmHour').value;
        const minute = document.getElementById('alarmMinute').value;
        const message = document.getElementById('alarmMessage').value;
        const repeat = document.getElementById('alarmRepeat').checked;

        if (!hour || !minute) {
            alert('時刻を入力してください');
            return;
        }

        const time = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;

        if (!time) {
            alert('時刻を入力してください');
            return;
        }

        if (!message) {
            alert('メッセージを入力してください');
            return;
        }

        try {
            // バックエンドにアラームを保存
            const response = await fetch('/api/alarms/set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    time: time,
                    label: 'アラーム',
                    message: message,
                    repeat: repeat
                })
            });

            const data = await response.json();

            if (data.success && data.alarm) {
                const alarm = data.alarm;
                this.alarms.push(alarm);
                this.scheduleAlarm(alarm);
                this.loadAlarmList();

                // フォームをクリア
                document.getElementById('alarmTime').value = '';
                document.getElementById('alarmMessage').value = '';
                document.getElementById('alarmRepeat').checked = false;

                console.log('✅ Alarm set:', alarm);
            } else {
                alert('アラーム設定に失敗しました: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Failed to set alarm:', error);
            alert('アラーム設定に失敗しました');
        }
    }

    scheduleAlarm(alarm) {
        const now = new Date();
        const [hours, minutes] = alarm.time.split(':').map(Number);

        const alarmTime = new Date();
        alarmTime.setHours(hours, minutes, 0, 0);

        // 既に過ぎていたら明日に設定
        const isNextDay = alarmTime <= now;
        if (isNextDay) {
            alarmTime.setDate(alarmTime.getDate() + 1);
        }

        const timeUntilAlarm = alarmTime - now;
        const minutesUntil = Math.round(timeUntilAlarm / 1000 / 60);
        const hoursUntil = Math.floor(minutesUntil / 60);
        const remainingMinutes = minutesUntil % 60;

        const timerId = setTimeout(() => {
            console.log(`🔔 Executing alarm: ${alarm.time} - ${alarm.message}`);
            this.triggerAlarm(alarm);
        }, timeUntilAlarm);

        this.alarmTimers.push({ id: alarm.id, timerId: timerId });

        const timeStr = hoursUntil > 0
            ? `${hoursUntil}時間${remainingMinutes}分後`
            : `${remainingMinutes}分後`;

        console.log(`⏰ Alarm scheduled:`, {
            time: alarm.time,
            message: alarm.message,
            scheduledFor: alarmTime.toLocaleString('ja-JP'),
            triggerIn: timeStr,
            isNextDay: isNextDay,
            currentTime: now.toLocaleString('ja-JP'),
            alarmId: alarm.id
        });
    }

    async triggerAlarm(alarm) {
        console.log('🔔 Alarm triggered:', alarm);

        try {
            // 1. まず鈴の音を再生
            console.log('🔔 Playing alarm sound...');
            await this.playAlarmSound();

            // 2. アラーム音が終わったら、メッセージを読み上げ
            console.log('📢 Playing alarm message...');
            const response = await fetch('/api/alarms/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: alarm.message
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Alarm trigger response:', data);

                if (data.success && data.audio) {
                    const audioBlob = this.base64ToBlob(data.audio, 'audio/wav');
                    const audioUrl = URL.createObjectURL(audioBlob);
                    await this.playAudioResponse(audioUrl);
                } else {
                    console.error('Alarm trigger failed:', data.error);
                }
            } else {
                console.error('Alarm trigger request failed:', response.status);
            }
        } catch (error) {
            console.error('Failed to play alarm:', error);
        }

        // 繰り返しの場合は再スケジュール
        if (alarm.repeat) {
            this.scheduleAlarm(alarm);
        } else {
            // 繰り返しでない場合はアラームを削除
            this.deleteAlarm(alarm.id);
        }
    }

    async loadAlarmList() {
        const alarmList = document.getElementById('alarmList');

        try {
            // バックエンドからアラーム一覧を取得
            const response = await fetch('/api/alarms/list');
            const data = await response.json();

            if (data.success && data.alarms) {
                // ローカルの配列も更新
                this.alarms = data.alarms;

                if (this.alarms.length === 0) {
                    alarmList.innerHTML = '<p class="alarm-empty">設定されているアラームはありません</p>';
                    return;
                }

                alarmList.innerHTML = this.alarms.map(alarm => `
                    <div class="alarm-item">
                        <div class="alarm-item-info">
                            <div class="alarm-item-time">${alarm.time} ${alarm.repeat ? '(毎日)' : ''}</div>
                            <div class="alarm-item-message">${alarm.message}</div>
                        </div>
                        <button class="alarm-item-delete" onclick="app.deleteAlarm('${alarm.id}')">削除</button>
                    </div>
                `).join('');

                // 既存のタイマーをクリア
                this.alarmTimers.forEach(timer => clearTimeout(timer.timerId));
                this.alarmTimers = [];

                // 全てのアラームをスケジュール
                this.alarms.forEach(alarm => this.scheduleAlarm(alarm));
            }
        } catch (error) {
            console.error('Failed to load alarms:', error);
            alarmList.innerHTML = '<p class="alarm-empty">アラーム一覧の取得に失敗しました</p>';
        }
    }

    async deleteAlarm(alarmId) {
        try {
            // バックエンドでアラームを削除
            const response = await fetch('/api/alarms/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    alarm_id: alarmId
                })
            });

            const data = await response.json();

            if (data.success) {
                // ローカルからも削除
                this.alarms = this.alarms.filter(a => a.id !== alarmId);

                // タイマーをキャンセル
                const timer = this.alarmTimers.find(t => t.id === alarmId);
                if (timer) {
                    clearTimeout(timer.timerId);
                    this.alarmTimers = this.alarmTimers.filter(t => t.id !== alarmId);
                }

                this.loadAlarmList();
                console.log('🗑️ Alarm deleted:', alarmId);
            } else {
                alert('アラーム削除に失敗しました: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Failed to delete alarm:', error);
            alert('アラーム削除に失敗しました');
        }
    }

    async loadTableTasks() {
        try {
            console.log('Loading table tasks...');

            const response = await fetch('/api/table/tasks');
            const data = await response.json();

            if (data.success && data.tasks) {
                this.tableTasks = data.tasks;
                this.renderTableTasks();
            }
        } catch (error) {
            console.error('Failed to load table tasks:', error);
            const tableList = document.getElementById('tableList');
            if (tableList) {
                tableList.innerHTML = '<div class="table-empty"><p>タスクの取得に失敗しました</p></div>';
            }
        }
    }

    renderTableTasks() {
        const tableList = document.getElementById('tableList');
        if (!tableList) return;

        if (this.tableTasks.length === 0) {
            tableList.innerHTML = '<div class="table-empty"><p>タスクはありません</p></div>';
            return;
        }

        tableList.innerHTML = this.tableTasks.map(task => {
            const statusText = task.status === 'processing' ? '処理中' : '完了';
            const statusClass = task.status === 'processing' ? 'processing' : 'completed';
            const timestamp = new Date(task.created_at).toLocaleString('ja-JP');

            return `
                <div class="table-item" data-task-id="${task.id}">
                    <div class="table-info">
                        <div class="table-title">${task.title}</div>
                        <div class="table-timestamp">${timestamp}</div>
                    </div>
                    <div class="table-status ${statusClass}">
                        ${statusText}
                    </div>
                </div>
            `;
        }).join('');

        // タスククリックイベントを追加
        document.querySelectorAll('.table-item').forEach(item => {
            item.addEventListener('click', () => {
                const taskId = item.getAttribute('data-task-id');
                this.openTableTaskDetail(taskId);
            });
        });
    }

    openTableTaskDetail(taskId) {
        const task = this.tableTasks.find(t => t.id === taskId);
        if (!task) return;

        const statusText = task.status === 'processing' ? '処理中' : '完了';
        const content = task.content || 'タスク内容なし';
        const result = task.result || (task.status === 'processing' ? '処理中...' : '結果なし');

        alert(`【${task.title}】\n\n状態: ${statusText}\n\n内容:\n${content}\n\n結果:\n${result}`);
    }

    async addTableTask(title, content, status = 'processing') {
        try {
            const response = await fetch('/api/table/tasks/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    status: status
                })
            });

            const data = await response.json();

            if (data.success) {
                await this.loadTableTasks();
                return data.task;
            }
        } catch (error) {
            console.error('Failed to add table task:', error);
        }
    }

    async updateTableTaskStatus(taskId, status, result = '') {
        try {
            const response = await fetch('/api/table/tasks/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: taskId,
                    status: status,
                    result: result
                })
            });

            const data = await response.json();

            if (data.success) {
                await this.loadTableTasks();
            }
        } catch (error) {
            console.error('Failed to update table task:', error);
        }
    }

    async loadAndScheduleAlarms() {
        try {
            // バックエンドからアラーム一覧を取得
            const response = await fetch('/api/alarms/list');
            const data = await response.json();

            if (data.success && data.alarms) {
                // ローカルの配列を更新
                this.alarms = data.alarms;

                // 既存のタイマーをクリア
                this.alarmTimers.forEach(timer => clearTimeout(timer.timerId));
                this.alarmTimers = [];

                // 全てのアラームをスケジュール
                this.alarms.forEach(alarm => this.scheduleAlarm(alarm));

                if (this.alarms.length > 0) {
                    console.log(`⏰ Loaded and scheduled ${this.alarms.length} alarm(s)`);
                }
            }
        } catch (error) {
            console.error('Failed to load and schedule alarms:', error);
        }
    }
}

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
    window.voiceAgent = new VoiceAgent();
    window.app = window.voiceAgent; // グローバルアクセス用
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

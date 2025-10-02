// UI Manager - ユーザーインターフェース管理

class UIManager {
    constructor() {
        this.elements = {};
        this.isSettingsOpen = false;
        this.messageCount = 0;
    }

    async init() {
        console.log('Initializing UI Manager...');

        // DOM要素の取得
        this.elements = {
            // ステータス表示
            agentImage: document.getElementById('agentImage'),

            // 会話エリア
            conversation: document.getElementById('conversation'),

            // テキスト入力
            textInput: document.getElementById('textInput'),
            sendButton: document.getElementById('sendButton'),

            // 設定
            settingsPanel: document.getElementById('settingsPanel'),
            settingsButton: document.getElementById('settingsButton'),

            // ステータスバー
            connectionStatus: document.getElementById('connectionStatus'),
            systemStatus: document.getElementById('systemStatus'),

            // 設定項目
            sttProvider: document.getElementById('sttProvider'),
            ttsProvider: document.getElementById('ttsProvider'),
            llmProvider: document.getElementById('llmProvider'),
            sensitivity: document.getElementById('sensitivity'),
            sensitivityValue: document.getElementById('sensitivityValue'),
            debugMode: document.getElementById('debugMode')
        };

        // 初期状態の設定
        this.setStatus('initializing', 'システム初期化中...');
        this.setConnectionStatus('connecting');

        // 自動スクロールの設定
        this.setupAutoScroll();

        console.log('UI Manager initialized successfully');
    }

    // 画像の状態を設定
    setFaceState(state) {
        const agentImage = this.elements.agentImage;
        if (!agentImage) return;

        // 既存のクラスを削除
        agentImage.classList.remove('speaking', 'listening', 'idle');

        // 新しい状態を設定
        agentImage.classList.add(state);
    }

    // ステータス管理
    setStatus(status, message) {
        console.log('Status updated:', status, message);
    }

    setConnectionStatus(status) {
        if (!this.elements.connectionStatus) return;

        const statusText = {
            connecting: '接続中...',
            connected: '接続済み',
            disconnected: '切断されました',
            error: '接続エラー'
        };

        this.elements.connectionStatus.textContent = statusText[status] || status;
        this.elements.connectionStatus.className = `connection-${status}`;
    }

    setSystemStatus(status) {
        if (!this.elements.systemStatus) return;

        const statusText = {
            ready: '準備完了',
            busy: '処理中',
            error: 'エラー',
            maintenance: 'メンテナンス中'
        };

        this.elements.systemStatus.textContent = statusText[status] || status;
    }

    // 録音状態の管理
    setRecordingState(isRecording) {
        const agentImage = this.elements.agentImage;
        const overlay = document.getElementById('imageOverlay');
        const overlayText = document.getElementById('overlayText');
        if (!agentImage) return;

        if (isRecording) {
            this.setFaceState('listening');

            // オーバーレイのテキストを変更
            if (overlayText) {
                overlayText.textContent = '録音中...';
            }

            // 現在の画像に応じて録音中の画像に変更（五条悟と初音ミクは変更しない）
            const currentSrc = agentImage.src;
            if (currentSrc.includes('fishw.png')) {
                agentImage.src = '/static/images/fishwfun.png';
            } else if (currentSrc.includes('fishm.png')) {
                agentImage.src = '/static/images/fishmfun.png';
            }
            // gojo.pngとmiku.png.webpは変更しない
        } else {
            this.setFaceState('idle');

            // オーバーレイのテキストを元に戻す
            if (overlayText) {
                overlayText.textContent = 'タッチで話しかけて';
            }

            // 録音終了時は元の画像に戻す（五条悟と初音ミクは変更しない）
            const currentSrc = agentImage.src;
            if (currentSrc.includes('fishwfun.png')) {
                agentImage.src = '/static/images/fishw.png';
            } else if (currentSrc.includes('fishmfun.png')) {
                agentImage.src = '/static/images/fishm.png';
            }
            // gojo.pngとmiku.png.webpは変更しない
        }
    }

    setSpeakingState(isSpeaking) {
        if (isSpeaking) {
            this.setStatus('speaking', '話しています...');
            this.setFaceState('speaking');
        } else {
            this.setStatus('ready', '話しかけてね');
            this.setFaceState('idle');
        }
    }

    setProcessingState(isProcessing) {
        const overlayText = document.getElementById('overlayText');
        if (!overlayText) return;

        if (isProcessing) {
            overlayText.textContent = '処理中...';
        } else {
            overlayText.textContent = 'タッチで話しかけて';
        }
    }


    // メッセージ管理
    addMessage(role, content, metadata = {}) {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.dataset.messageId = ++this.messageCount;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // マークダウンライクなテキスト処理（簡易版）
        const processedContent = this.processMessageContent(content);
        contentDiv.innerHTML = processedContent;

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('ja-JP');

        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);

        // メタデータの処理
        if (metadata.audioUrl) {
            const audioButton = document.createElement('button');
            audioButton.className = 'audio-play-button';
            audioButton.textContent = '🔊 再生';
            audioButton.onclick = () => this.playMessageAudio(metadata.audioUrl);
            messageDiv.appendChild(audioButton);
        }

        conversation.appendChild(messageDiv);

        // 自動スクロール
        this.scrollToBottom();

        // メッセージ数制限
        this.limitMessageHistory();

        console.log('Added message:', role, content);
    }

    processMessageContent(content) {
        // 簡易的なマークダウン処理
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    addToolResult(toolName, result) {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        const toolDiv = document.createElement('div');
        toolDiv.className = 'tool-result';

        toolDiv.innerHTML = `
            <div class="tool-header">
                <span class="tool-icon">🔧</span>
                <span class="tool-name">${toolName}</span>
            </div>
            <div class="tool-content">${this.formatToolResult(result)}</div>
        `;

        conversation.appendChild(toolDiv);
        this.scrollToBottom();

        console.log('Added tool result:', toolName, result);
    }

    formatToolResult(result) {
        if (typeof result === 'object') {
            return `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        }
        return String(result);
    }

    clearConversation() {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        // システムメッセージ以外を削除
        const messages = conversation.querySelectorAll('.message:not(.system)');
        messages.forEach(message => message.remove());

        // ツール結果も削除
        const toolResults = conversation.querySelectorAll('.tool-result');
        toolResults.forEach(result => result.remove());

        this.messageCount = 0;
        console.log('Conversation cleared');
    }

    limitMessageHistory() {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        const messages = conversation.querySelectorAll('.message');
        const maxMessages = 50; // 最大メッセージ数

        if (messages.length > maxMessages) {
            const deleteCount = messages.length - maxMessages;
            for (let i = 0; i < deleteCount; i++) {
                if (messages[i] && !messages[i].classList.contains('system')) {
                    messages[i].remove();
                }
            }
        }
    }

    scrollToBottom() {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        setTimeout(() => {
            conversation.scrollTop = conversation.scrollHeight;
        }, 100);
    }

    setupAutoScroll() {
        const conversation = this.elements.conversation;
        if (!conversation) return;

        // ユーザーがスクロールしているかを検知
        let isUserScrolling = false;
        let scrollTimeout;

        conversation.addEventListener('scroll', () => {
            isUserScrolling = true;

            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // 最下部付近にいる場合は自動スクロールを再開
                const isNearBottom = conversation.scrollTop + conversation.clientHeight >=
                                   conversation.scrollHeight - 100;
                isUserScrolling = !isNearBottom;
            }, 150);
        });

        // 自動スクロール機能を改良
        this.scrollToBottom = () => {
            if (!isUserScrolling) {
                setTimeout(() => {
                    conversation.scrollTop = conversation.scrollHeight;
                }, 100);
            }
        };
    }

    // 設定パネル管理
    toggleSettings() {
        this.isSettingsOpen = !this.isSettingsOpen;

        const panel = this.elements.settingsPanel;
        const button = document.getElementById('settingsButton');

        if (!panel) return;

        if (this.isSettingsOpen) {
            panel.classList.add('open');
            if (button) button.classList.add('active');
        } else {
            panel.classList.remove('open');
            if (button) button.classList.remove('active');
        }

        console.log('Settings panel toggled:', this.isSettingsOpen);
    }

    closeSettings() {
        if (!this.isSettingsOpen) return;

        this.isSettingsOpen = false;
        const panel = this.elements.settingsPanel;
        const button = document.getElementById('settingsButton');

        if (panel) {
            panel.classList.remove('open');
        }
        if (button) {
            button.classList.remove('active');
        }
    }

    // エラー表示
    showError(message) {
        // エラーメッセージをトーストとして表示
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.textContent = message;

        document.body.appendChild(toast);

        // アニメーション
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 5000);

        console.error('Error shown to user:', message);
    }

    showSuccess(message) {
        // 成功メッセージをトーストとして表示
        const toast = document.createElement('div');
        toast.className = 'success-toast';
        toast.textContent = message;

        document.body.appendChild(toast);

        // アニメーション
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);

        console.log('Success shown to user:', message);
    }

    // 音声再生
    async playMessageAudio(audioUrl) {
        try {
            const audio = new Audio(audioUrl);
            await audio.play();
        } catch (error) {
            console.error('Failed to play message audio:', error);
            this.showError('音声の再生に失敗しました');
        }
    }

    // 音量レベル表示
    updateVolumeLevel(level) {
        const agentImage = this.elements.agentImage;
        if (!agentImage) return;

        // 音量レベルに応じて画像のサイズを変更
        const scale = 1 + (level * 0.2); // 1.0 〜 1.2の範囲
        agentImage.style.transform = `scale(${scale})`;
    }

    // デバッグ情報表示
    showDebugInfo(info) {
        if (!this.elements.debugMode || !this.elements.debugMode.checked) return;

        console.log('Debug info:', info);

        // デバッグ情報をUIに表示（開発時のみ）
        const debugPanel = document.getElementById('debugPanel');
        if (debugPanel) {
            debugPanel.innerHTML = `<pre>${JSON.stringify(info, null, 2)}</pre>`;
        }
    }

    // 設定値の取得
    getSettings() {
        return {
            sttProvider: this.elements.sttProvider?.value,
            ttsProvider: this.elements.ttsProvider?.value,
            llmProvider: this.elements.llmProvider?.value,
            sensitivity: parseInt(this.elements.sensitivity?.value || 50),
            debugMode: this.elements.debugMode?.checked || false
        };
    }

    // 設定値の更新
    updateSettings(settings) {
        if (settings.sttProvider && this.elements.sttProvider) {
            this.elements.sttProvider.value = settings.sttProvider;
        }
        if (settings.ttsProvider && this.elements.ttsProvider) {
            this.elements.ttsProvider.value = settings.ttsProvider;
        }
        if (settings.llmProvider && this.elements.llmProvider) {
            this.elements.llmProvider.value = settings.llmProvider;
        }
        if (settings.sensitivity && this.elements.sensitivity) {
            this.elements.sensitivity.value = settings.sensitivity;
            if (this.elements.sensitivityValue) {
                this.elements.sensitivityValue.textContent = settings.sensitivity;
            }
        }
        if (typeof settings.debugMode === 'boolean' && this.elements.debugMode) {
            this.elements.debugMode.checked = settings.debugMode;
        }
    }
}
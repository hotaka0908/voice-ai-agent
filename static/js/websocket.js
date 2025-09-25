// WebSocket Manager - WebSocket通信管理

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.eventListeners = {};

        this.voiceWs = null; // 音声用WebSocket
        this.chatWs = null;  // チャット用WebSocket
    }

    async init() {
        console.log('Initializing WebSocket Manager...');
        await this.connect();
    }

    async connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;

            // チャット用WebSocketの接続
            const chatUrl = `${protocol}//${host}/ws/chat`;
            this.chatWs = new WebSocket(chatUrl);

            this.chatWs.onopen = () => {
                console.log('Chat WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connect');
            };

            this.chatWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Received message:', data);
                    this.emit('message', data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.chatWs.onclose = () => {
                console.log('Chat WebSocket disconnected');
                this.isConnected = false;
                this.emit('disconnect');
                this.handleReconnect();
            };

            this.chatWs.onerror = (error) => {
                console.error('Chat WebSocket error:', error);
                this.emit('error', error);
            };

            // 音声用WebSocketの接続
            const voiceUrl = `${protocol}//${host}/ws/voice`;
            this.voiceWs = new WebSocket(voiceUrl);

            this.voiceWs.onopen = () => {
                console.log('Voice WebSocket connected');
            };

            this.voiceWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('🎤 VOICE WebSocket received:', data);
                    console.log('🎤 Message type:', data.type);
                    console.log('🎤 Message content:', data.content);

                    // 音声から認識されたメッセージをチャット欄に表示
                    if (data.type === 'user_message' || data.type === 'assistant_message') {
                        console.log('🎤 Emitting voiceMessage event:', data);
                        this.emit('voiceMessage', data);
                    } else {
                        console.log('🎤 Emitting regular message event:', data);
                        this.emit('message', data);
                    }
                } catch (error) {
                    console.error('❌ Failed to parse voice WebSocket message:', error);
                    console.error('❌ Raw message:', event.data);
                }
            };

            this.voiceWs.onclose = () => {
                console.log('Voice WebSocket disconnected');
            };

            this.voiceWs.onerror = (error) => {
                console.error('Voice WebSocket error:', error);
            };

        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.emit('error', error);
            this.handleReconnect();
        }
    }

    handleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    async sendTextMessage(text) {
        if (!this.isConnected || !this.chatWs) {
            throw new Error('WebSocket not connected');
        }

        const message = {
            type: 'text',
            content: text,
            timestamp: new Date().toISOString()
        };

        this.chatWs.send(JSON.stringify(message));
        console.log('Sent text message:', text);
    }

    async sendAudioData(audioData) {
        if (!this.voiceWs || this.voiceWs.readyState !== WebSocket.OPEN) {
            throw new Error('Voice WebSocket not connected');
        }

        // 音声データをそのまま送信
        this.voiceWs.send(audioData);
        console.log('Sent audio data:', audioData.byteLength, 'bytes');
    }

    async updateConfig(config) {
        if (!this.isConnected || !this.chatWs) {
            throw new Error('WebSocket not connected');
        }

        const message = {
            type: 'config_update',
            config: config,
            timestamp: new Date().toISOString()
        };

        this.chatWs.send(JSON.stringify(message));
        console.log('Sent config update:', config);
    }

    async resetConversation() {
        if (!this.isConnected || !this.chatWs) {
            throw new Error('WebSocket not connected');
        }

        const message = {
            type: 'reset',
            timestamp: new Date().toISOString()
        };

        this.chatWs.send(JSON.stringify(message));
        console.log('Sent conversation reset request');
    }

    async getSystemStatus() {
        if (!this.isConnected || !this.chatWs) {
            throw new Error('WebSocket not connected');
        }

        const message = {
            type: 'status_request',
            timestamp: new Date().toISOString()
        };

        this.chatWs.send(JSON.stringify(message));
        console.log('Requested system status');
    }

    // イベント処理
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        this.eventListeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.eventListeners[event]) return;

        const index = this.eventListeners[event].indexOf(callback);
        if (index > -1) {
            this.eventListeners[event].splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.eventListeners[event]) return;

        this.eventListeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('Event listener error:', error);
            }
        });
    }

    disconnect() {
        console.log('Disconnecting WebSocket...');

        if (this.chatWs) {
            this.chatWs.close();
            this.chatWs = null;
        }

        if (this.voiceWs) {
            this.voiceWs.close();
            this.voiceWs = null;
        }

        this.isConnected = false;
        this.reconnectAttempts = 0;
    }

    getConnectionStatus() {
        return {
            connected: this.isConnected,
            chatWebSocket: this.chatWs ? this.chatWs.readyState : WebSocket.CLOSED,
            voiceWebSocket: this.voiceWs ? this.voiceWs.readyState : WebSocket.CLOSED,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}
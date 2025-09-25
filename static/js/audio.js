// Audio Manager - 音声録音・再生管理

class AudioManager {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.isRecording = false;
        this.isMuted = false;
        this.audioChunks = [];
        this.stream = null;
        this.eventListeners = {};

        // 設定
        this.config = {
            sampleRate: 16000,
            channels: 1,
            bitDepth: 16,
            bufferSize: 1024,
            silenceThreshold: 0.01,
            silenceTimeout: 2000, // 2秒の無音で録音停止
            maxRecordingTime: 30000 // 30秒の最大録音時間
        };

        // 録音タイマー
        this.silenceTimer = null;
        this.recordingTimer = null;
    }

    async init() {
        console.log('Initializing Audio Manager...');

        try {
            // ブラウザの対応チェック
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('MediaDevices API not supported');
            }

            // 音声コンテキストの作成
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

            console.log('Audio Manager initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Audio Manager:', error);
            throw error;
        }
    }

    async startRecording() {
        try {
            console.log('Starting audio recording...');

            // マイクアクセスの許可を取得
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: this.config.channels,
                    sampleRate: this.config.sampleRate,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // AudioContextが停止している場合は再開
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            // MediaRecorderの設定
            const options = {
                mimeType: this.getSupportedMimeType(),
                audioBitsPerSecond: this.config.sampleRate * this.config.bitDepth
            };

            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];

            // イベントリスナーの設定
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.handleRecordingComplete();
            };

            // 音声解析の設定
            await this.setupAudioAnalysis();

            // 録音開始
            this.mediaRecorder.start(100); // 100ms間隔でデータを取得
            this.isRecording = true;

            // タイマーの設定
            this.startSilenceDetection();
            this.startRecordingTimer();

            console.log('Audio recording started');

        } catch (error) {
            console.error('Failed to start recording:', error);
            throw error;
        }
    }

    async stopRecording() {
        try {
            console.log('Stopping audio recording...');

            this.isRecording = false;

            // タイマーのクリア
            this.clearTimers();

            // MediaRecorderの停止
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.stop();
            }

            // ストリームの停止
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }

            console.log('Audio recording stopped');

        } catch (error) {
            console.error('Failed to stop recording:', error);
            throw error;
        }
    }

    async setupAudioAnalysis() {
        try {
            // マイクからの音声をAnalyserNodeに接続
            this.microphone = this.audioContext.createMediaStreamSource(this.stream);
            this.analyser = this.audioContext.createAnalyser();

            this.analyser.fftSize = this.config.bufferSize;
            this.analyser.smoothingTimeConstant = 0.3;

            this.microphone.connect(this.analyser);

            // 音声レベルの監視開始
            this.startVolumeMonitoring();

        } catch (error) {
            console.error('Failed to setup audio analysis:', error);
        }
    }

    startVolumeMonitoring() {
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkVolume = () => {
            if (!this.isRecording) return;

            this.analyser.getByteFrequencyData(dataArray);

            // RMS値を計算
            let rms = 0;
            for (let i = 0; i < bufferLength; i++) {
                rms += dataArray[i] * dataArray[i];
            }
            rms = Math.sqrt(rms / bufferLength) / 255;

            // 音声レベルをイベントで通知
            this.emit('volumeLevel', rms);

            // 無音検出
            if (rms < this.config.silenceThreshold) {
                if (!this.silenceTimer) {
                    this.silenceTimer = setTimeout(() => {
                        console.log('Silence detected, stopping recording');
                        this.stopRecording();
                    }, this.config.silenceTimeout);
                }
            } else {
                // 音声が検出されたら無音タイマーをリセット
                if (this.silenceTimer) {
                    clearTimeout(this.silenceTimer);
                    this.silenceTimer = null;
                }
            }

            // 次のフレームで再実行
            requestAnimationFrame(checkVolume);
        };

        checkVolume();
    }

    startSilenceDetection() {
        // 無音検出は setupVolumeMonitoring で行う
    }

    startRecordingTimer() {
        this.recordingTimer = setTimeout(() => {
            console.log('Max recording time reached, stopping recording');
            this.stopRecording();
        }, this.config.maxRecordingTime);
    }

    clearTimers() {
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
        }

        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    async handleRecordingComplete() {
        try {
            if (this.audioChunks.length === 0) {
                console.warn('No audio data recorded');
                return;
            }

            // 音声データをBlobに変換
            const audioBlob = new Blob(this.audioChunks, {
                type: this.getSupportedMimeType()
            });

            // WAV形式に変換（必要に応じて）
            const audioBuffer = await this.convertToWAV(audioBlob);

            // 音声データイベントを発火
            this.emit('audioData', audioBuffer);

            console.log('Audio recording processed:', audioBuffer.byteLength, 'bytes');

        } catch (error) {
            console.error('Failed to handle recording completion:', error);
        }
    }

    async convertToWAV(audioBlob) {
        try {
            // ブラウザがWAVをサポートしている場合はそのまま返す
            if (this.getSupportedMimeType().includes('wav')) {
                return await audioBlob.arrayBuffer();
            }

            // 他の形式の場合は AudioContext で WAV に変換
            const arrayBuffer = await audioBlob.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

            return this.audioBufferToWAV(audioBuffer);

        } catch (error) {
            console.error('Failed to convert audio to WAV:', error);
            // 変換に失敗した場合は元のデータを返す
            return await audioBlob.arrayBuffer();
        }
    }

    audioBufferToWAV(audioBuffer) {
        const length = audioBuffer.length;
        const sampleRate = audioBuffer.sampleRate;
        const numChannels = Math.min(audioBuffer.numberOfChannels, 1); // モノラルに変換

        // WAVファイルのサイズを計算
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);

        // WAVヘッダーの書き込み
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * 2, true);

        // 音声データの書き込み
        const channelData = audioBuffer.getChannelData(0);
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, channelData[i]));
            view.setInt16(offset, sample * 0x7FFF, true);
            offset += 2;
        }

        return arrayBuffer;
    }

    async playAudio(audioUrl) {
        try {
            console.log('Playing audio:', audioUrl);

            const audio = new Audio(audioUrl);

            return new Promise((resolve, reject) => {
                audio.onended = () => {
                    console.log('Audio playback finished');
                    resolve();
                };

                audio.onerror = (error) => {
                    console.error('Audio playback error:', error);
                    reject(error);
                };

                // ミュート状態をチェック
                if (this.isMuted) {
                    audio.muted = true;
                }

                audio.play().catch(reject);
            });

        } catch (error) {
            console.error('Failed to play audio:', error);
            throw error;
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        console.log('Audio muted:', this.isMuted);
        return this.isMuted;
    }

    getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg',
            'audio/wav',
            'audio/mp4',
            'audio/mpeg'
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }

        return 'audio/webm'; // fallback
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

    getStatus() {
        return {
            isRecording: this.isRecording,
            isMuted: this.isMuted,
            audioContext: this.audioContext ? this.audioContext.state : 'null',
            supportedMimeType: this.getSupportedMimeType()
        };
    }

    async cleanup() {
        console.log('Cleaning up Audio Manager...');

        await this.stopRecording();

        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }

        this.eventListeners = {};
        console.log('Audio Manager cleanup completed');
    }
}
/**
 * Camera Management - カメラ撮影と画像分析
 */

class CameraManager {
    constructor() {
        this.stream = null;
        this.videoElement = null;
        this.canvasElement = null;
        this.isActive = false;
    }

    /**
     * カメラを初期化
     */
    async initialize() {
        this.videoElement = document.getElementById('cameraVideo');
        this.canvasElement = document.getElementById('cameraCanvas');

        if (!this.videoElement || !this.canvasElement) {
            console.error('Camera elements not found');
            return false;
        }

        return true;
    }

    /**
     * カメラを起動
     */
    async startCamera() {
        try {
            // カメラアクセス許可を要求
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // 背面カメラを優先（モバイル対応）
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });

            this.videoElement.srcObject = this.stream;
            await this.videoElement.play();
            this.isActive = true;

            console.log('Camera started successfully');
            return true;

        } catch (error) {
            console.error('Failed to start camera:', error);
            alert('カメラの起動に失敗しました。カメラへのアクセスを許可してください。');
            return false;
        }
    }

    /**
     * カメラを停止
     */
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }

        this.isActive = false;
        console.log('Camera stopped');
    }

    /**
     * 画像をキャプチャ
     * @returns {string} Base64エンコードされた画像データ
     */
    captureImage() {
        if (!this.isActive || !this.videoElement || !this.canvasElement) {
            console.error('Camera is not active');
            return null;
        }

        const context = this.canvasElement.getContext('2d');
        const width = this.videoElement.videoWidth;
        const height = this.videoElement.videoHeight;

        // キャンバスサイズを動画サイズに合わせる
        this.canvasElement.width = width;
        this.canvasElement.height = height;

        // 動画フレームをキャンバスに描画
        context.drawImage(this.videoElement, 0, 0, width, height);

        // Base64エンコード
        const imageData = this.canvasElement.toDataURL('image/jpeg', 0.8);
        console.log('Image captured, size:', imageData.length);

        return imageData;
    }

    /**
     * 画像を分析（サーバーに送信）
     * @param {string} query - 分析クエリ
     * @returns {Promise<object>} 分析結果
     */
    async analyzeImage(query = 'この画像について詳しく教えてください') {
        const imageData = this.captureImage();

        if (!imageData) {
            throw new Error('画像のキャプチャに失敗しました');
        }

        try {
            // サーバーにPOSTリクエスト
            const response = await fetch('/api/vision/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageData,
                    query: query
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const result = await response.json();
            console.log('Vision analysis result:', result);

            return result;

        } catch (error) {
            console.error('Vision analysis failed:', error);
            throw error;
        }
    }

    /**
     * カメラの状態を取得
     */
    getStatus() {
        return {
            isActive: this.isActive,
            hasStream: !!this.stream,
            videoReady: this.videoElement && this.videoElement.readyState === 4
        };
    }
}

// グローバルインスタンス
const cameraManager = new CameraManager();

// DOMロード後に初期化
document.addEventListener('DOMContentLoaded', async () => {
    await cameraManager.initialize();

    // カメラボタンのイベントリスナー
    const cameraButton = document.getElementById('cameraButton');
    const cameraDialog = document.getElementById('cameraDialog');
    const closeCameraDialog = document.getElementById('closeCameraDialog');
    const startCameraBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    const stopCameraBtn = document.getElementById('stopCameraBtn');
    const visionResult = document.getElementById('visionResult');

    // カメラダイアログを開く
    cameraButton?.addEventListener('click', () => {
        cameraDialog.style.display = 'flex';
    });

    // カメラダイアログを閉じる
    closeCameraDialog?.addEventListener('click', () => {
        cameraDialog.style.display = 'none';
        cameraManager.stopCamera();
    });

    // カメラ起動
    startCameraBtn?.addEventListener('click', async () => {
        const success = await cameraManager.startCamera();
        if (success) {
            startCameraBtn.style.display = 'none';
            captureBtn.style.display = 'inline-block';
            stopCameraBtn.style.display = 'inline-block';
        }
    });

    // 画像キャプチャ・分析
    captureBtn?.addEventListener('click', async () => {
        try {
            captureBtn.disabled = true;
            captureBtn.textContent = '分析中...';

            // 画像を分析
            const result = await cameraManager.analyzeImage('この画像に何が写っていますか？詳しく教えてください。');

            // 結果を表示
            if (result.success) {
                visionResult.innerHTML = `
                    <div class="vision-success">
                        <h4>✅ 分析完了</h4>
                        <p>${result.result.replace(/\n/g, '<br>')}</p>
                    </div>
                `;

                // 音声で読み上げ（audio_urlがある場合）
                if (result.audio_url && window.audioPlayer) {
                    window.audioPlayer.src = result.audio_url;
                    await window.audioPlayer.play();
                }
            } else {
                visionResult.innerHTML = `
                    <div class="vision-error">
                        <h4>❌ エラー</h4>
                        <p>${result.error || '分析に失敗しました'}</p>
                    </div>
                `;
            }

        } catch (error) {
            visionResult.innerHTML = `
                <div class="vision-error">
                    <h4>❌ エラー</h4>
                    <p>${error.message}</p>
                </div>
            `;
        } finally {
            captureBtn.disabled = false;
            captureBtn.textContent = '📸 撮影して分析';
        }
    });

    // カメラ停止
    stopCameraBtn?.addEventListener('click', () => {
        cameraManager.stopCamera();
        startCameraBtn.style.display = 'inline-block';
        captureBtn.style.display = 'none';
        stopCameraBtn.style.display = 'none';
        visionResult.innerHTML = '';
    });
});

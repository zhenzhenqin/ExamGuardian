(() => {
    function init() {
        const panel = document.querySelector('#exam-guardian-media');
        const form = document.querySelector('#responseform');
        if (!panel || !form) {
            return;
        }
        form.before(panel);
        panel.hidden = false;

        const start = panel.querySelector('[data-media-start]');
        const stop = panel.querySelector('[data-media-stop]');
        const retry = panel.querySelector('[data-media-retry]');
        const video = panel.querySelector('[data-media-video]');
        const level = panel.querySelector('[data-media-level]');
        const status = panel.querySelector('[data-media-status]');
        let stream, context, timer, meterTimer, recorder, pending;
        let leaving = false;
        let generation = 0;

        function release() {
            generation += 1;
            clearTimeout(timer);
            clearInterval(meterTimer);
            if (recorder?.state === 'recording') recorder.stop();
            recorder = null;
            stream?.getTracks().forEach(track => track.stop());
            stream = null;
            context?.close().catch(() => {});
            context = null;
            video.srcObject = null;
            video.hidden = true;
            level.value = 0;
            start.disabled = false;
            stop.disabled = true;
        }

        function finish() {
            if (recorder?.state === 'recording') {
                clearTimeout(timer);
                stop.disabled = true;
                recorder.stop();
                status.textContent = '正在生成片段…';
                return;
            }
            release();
            status.textContent = '已停止测试并释放设备。';
        }

        async function upload() {
            start.disabled = true;
            retry.hidden = true;
            status.textContent = '正在保存片段…';
            const body = new FormData();
            body.append('sesskey', panel.dataset.sesskey);
            body.append('attempt', panel.dataset.attempt);
            body.append('clipkey', pending.key);
            body.append('capturems', pending.capture);
            body.append('durationms', pending.duration);
            body.append('clip', pending.blob, 'evidence.webm');
            const controller = new AbortController();
            const deadline = setTimeout(() => controller.abort(), 15000);
            try {
                const response = await fetch(panel.dataset.upload, {method: 'POST', body, signal: controller.signal});
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.error || '服务器未保存片段。');
                }
                status.textContent = `已保存片段 EG-${result.id}。`;
                pending = null;
                start.disabled = false;
            } catch (error) {
                status.textContent = '保存失败。' + (error.name === 'AbortError' ? '请求超时。' : error.message);
                retry.hidden = false;
                start.disabled = false;
            } finally {
                clearTimeout(deadline);
            }
        }

        start.addEventListener('click', async () => {
            const request = ++generation;
            pending = null;
            retry.hidden = true;
            start.disabled = true;
            stop.disabled = false;
            status.textContent = '等待设备授权…';

            try {
                if (!navigator.mediaDevices?.getUserMedia) {
                    throw new Error('当前页面无法调用 getUserMedia');
                }
                const webm = 'video/webm;codecs=vp8,opus';
                if (panel.dataset.upload && !window.MediaRecorder?.isTypeSupported(webm)) {
                    throw new Error('当前浏览器无法录制 WebM 音视频');
                }
                context = new AudioContext();
                context.resume().catch(() => {});
                const media = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: {width: {ideal: 320}, height: {ideal: 180}, frameRate: {max: 15}}
                });
                if (request !== generation) {
                    media.getTracks().forEach(track => track.stop());
                    return;
                }

                stream = media;
                video.srcObject = stream;
                video.hidden = false;
                const analyser = context.createAnalyser();
                context.createMediaStreamSource(stream).connect(analyser);
                const samples = new Uint8Array(analyser.fftSize);
                meterTimer = setInterval(() => {
                    analyser.getByteTimeDomainData(samples);
                    level.value = Math.sqrt(samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / samples.length);
                }, 100);
                if (panel.dataset.upload) {
                    const key = Array.from(crypto.getRandomValues(new Uint8Array(12)), value => value.toString(16).padStart(2, '0')).join('');
                    const capture = Date.now();
                    const started = performance.now();
                    const chunks = [];
                    recorder = new MediaRecorder(media, {mimeType: webm});
                    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
                    recorder.onerror = () => {
                        if (request === generation) {
                            release();
                            recorder = null;
                            status.textContent = '录制失败，请重试。';
                        }
                    };
                    recorder.onstop = () => {
                        if (leaving || request !== generation) {
                            return;
                        }
                        const duration = Math.round(performance.now() - started);
                        const blob = new Blob(chunks, {type: 'video/webm'});
                        recorder = null;
                        release();
                        if (blob.size < 32) {
                            status.textContent = '片段为空，请录制几秒再停止。';
                            return;
                        }
                        pending = {key, capture, duration, blob};
                        upload();
                    };
                    recorder.start(1000);
                }
                timer = setTimeout(finish, 10000);
                await video.play();
                if (request === generation && !stop.disabled) {
                    const action = panel.dataset.upload ? '正在录制' : '已获取音频和视频轨道';
                    status.textContent = `${action}，画面 ${video.videoWidth} × ${video.videoHeight}。`;
                }
            } catch (error) {
                if (request !== generation) {
                    return;
                }
                release();
                status.textContent = `测试失败（${error.name}） ${error.message}`;
            }
        });

        stop.addEventListener('click', finish);
        retry.addEventListener('click', upload);
        window.addEventListener('pagehide', () => {
            leaving = true;
            release();
        });
        window.addEventListener('pageshow', event => {
            if (event.persisted) leaving = false;
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, {once: true});
    } else {
        init();
    }
})();

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
        const video = panel.querySelector('[data-media-video]');
        const level = panel.querySelector('[data-media-level]');
        const status = panel.querySelector('[data-media-status]');
        let stream, context, timer, meterTimer;
        let generation = 0;

        function release() {
            generation += 1;
            clearTimeout(timer);
            clearInterval(meterTimer);
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
            release();
            status.textContent = '已停止测试并释放设备。';
        }

        start.addEventListener('click', async () => {
            const request = ++generation;
            start.disabled = true;
            stop.disabled = false;
            status.textContent = '等待设备授权…';

            try {
                if (!navigator.mediaDevices?.getUserMedia) {
                    throw new Error('当前页面无法调用 getUserMedia');
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
                timer = setTimeout(finish, 10000);
                await video.play();
                if (request === generation) {
                    status.textContent = `已获取音频和视频轨道，画面 ${video.videoWidth} × ${video.videoHeight}。`;
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
        window.addEventListener('pagehide', release);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, {once: true});
    } else {
        init();
    }
})();

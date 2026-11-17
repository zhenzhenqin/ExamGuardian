// Test fixture for ordinary Chromium. Exports live canvas and Web Audio tracks.
Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
    configurable: true,
    value: async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 320;
        canvas.height = 180;
        const image = canvas.getContext("2d");
        const start = performance.now();
        function paint() {
            const elapsed = performance.now() - start;
            image.fillStyle = "#193941";
            image.fillRect(0, 0, 320, 180);
            image.fillStyle = "#e7c07a";
            image.fillRect((elapsed / 8) % 260, 46, 60, 35);
            image.fillStyle = "white";
            image.font = "20px monospace";
            image.fillText("Test " + (elapsed / 1000).toFixed(2), 14, 144);
        }
        paint();
        const timer = setInterval(paint, 40);
        const pictures = canvas.captureStream(20);
        const audio = new AudioContext({sampleRate: 48000});
        const destination = audio.createMediaStreamDestination();
        const level = audio.createGain();
        const tone = audio.createOscillator();
        level.gain.value = 0.015;
        tone.frequency.value = 440;
        tone.connect(level).connect(destination);
        tone.start();
        await audio.resume();
        window.addEventListener("pagehide", () => {
            clearInterval(timer);
            void audio.close();
        }, {once: true});
        return new MediaStream([...pictures.getVideoTracks(), ...destination.stream.getAudioTracks()]);
    },
});

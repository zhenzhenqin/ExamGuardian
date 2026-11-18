(() => {
    function init() {
    const panel = document.querySelector("[data-eg-capture]");
    if (!panel) return;
    const quiz = document.querySelector("#responseform");
    if (quiz) quiz.before(panel);
    panel.hidden = false;
    const start = panel.querySelector("[data-eg-start]");
    const stop = panel.querySelector("[data-eg-stop]");
    const decline = panel.querySelector("[data-eg-decline]");
    const video = panel.querySelector("[data-eg-preview]");
    const status = panel.querySelector("[data-eg-status]");
    const selection = "exam-guardian:" + panel.dataset.attempt;
    const segmentTypes = ["video/webm;codecs=vp8,opus", "video/webm;codecs=vp9,opus", "video/webm"];
    const maxQueuedBytes = 32 * 1024 * 1024;
    let session, stream, recorder, rollover, anchor, database;
    let active = false;
    let sending = false;
    let retryTimer;
    let retryWait = 1000;
    let uploaded = 0;
    let userPaused = false;
    let storageWarning = false;
    let dropped = false;
    let queue = [];
    const events = [];
    const inFlight = new Map();

    function selectionValue(value) {
        try {
            if (value !== undefined) sessionStorage.setItem(selection, value);
            return sessionStorage.getItem(selection);
        } catch {
            return null;
        }
    }

    function elapsed() {
        return Math.max(0, Math.round(performance.now() - anchor));
    }

    function show(message) {
        status.textContent = message;
        if (storageWarning) status.textContent += " 页面存储不可用，翻页可能丢失待传片段。";
        if (dropped) status.textContent += " 本次录制包含缺失片段。";
    }

    async function openQueue() {
        if (!window.indexedDB) throw new Error("IndexedDB unavailable");
        return new Promise((resolve, reject) => {
            const request = indexedDB.open("exam-guardian-pending", 1);
            request.onupgradeneeded = () => request.result.createObjectStore("clips", {keyPath: "key"});
            request.onsuccess = () => resolve(request.result);
            request.onerror = request.onblocked = () => reject(request.error);
        });
    }

    async function pending(mode, callback) {
        if (!database) throw new Error("IndexedDB unavailable");
        return new Promise((resolve, reject) => {
            const tx = database.transaction("clips", mode);
            const request = callback(tx.objectStore("clips"));
            tx.oncomplete = () => resolve(request.result);
            tx.onabort = tx.onerror = () => reject(tx.error);
        });
    }

    function forget(clip) {
        queue = queue.filter(item => item.key !== clip.key);
        return pending("readwrite", store => store.delete(clip.key)).catch(() => { storageWarning = true; });
    }

    async function restore() {
        try {
            database ||= await openQueue();
            const entries = await pending("readonly", store => store.getAll());
            const known = new Set(queue.map(clip => clip.key));
            for (const clip of entries) {
                if (Date.now() - clip.createdAt > 4 * 60 * 60 * 1000) {
                    await pending("readwrite", store => store.delete(clip.key));
                } else if (clip.sessionId === session.sessionId && !known.has(clip.key)) {
                    queue.push(clip);
                }
            }
            queue.sort((a, b) => a.startMs - b.startMs);
        } catch {
            storageWarning = true;
            // The current page can still send and retry its in-memory queue.
        }
    }

    function event(code) {
        if (!session?.token || events.length >= 25) return;
        events.push({key: crypto.randomUUID(), code, atMs: elapsed()});
        void flush();
    }

    function send(url, body, json = false) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        const headers = {Authorization: "Bearer " + session.token};
        if (json) headers["Content-Type"] = "application/json";
        return fetch(url, {
            method: "POST", body: json ? JSON.stringify(body) : body,
            credentials: "omit", headers, signal: controller.signal,
        }).finally(() => clearTimeout(timer));
    }

    async function flush() {
        if (sending || !session?.token) return;
        sending = true;
        clearTimeout(retryTimer);
        try {
            while (queue.length || events.length) {
                if (events.length) {
                    const response = await send(session.eventUrl, events[0], true);
                    if (response.status >= 500 || response.status === 429) throw new Error("retry");
                    events.shift();
                }
                if (queue.length) {
                    const clip = queue[0];
                    const body = new FormData();
                    for (const key of ["key", "startMs", "endMs", "deviceAtMs"]) body.append(key, clip[key]);
                    body.append("clip", clip.blob, "capture.webm");
                    const response = await send(session.segmentUrl, body);
                    if (response.status >= 500 || response.status === 429) throw new Error("retry");
                    if (response.status === 403) {
                        stopRecording();
                        show("录制会话已失效。请刷新作答页后恢复采集。");
                        return;
                    }
                    const problem = response.ok ? null : await response.json().catch(() => null);
                    await forget(clip);
                    if (response.ok) {
                        uploaded++;
                    } else {
                        dropped = true;
                        event("segment_rejected");
                    }
                    const summary = (active ? "正在录制" : "录制已暂停") + "。本页已确认 " + uploaded + " 段，待传 " + queue.length + " 段。";
                    show(problem?.error ? summary + " " + problem.error : summary);
                }
            }
            retryWait = 1000;
        } catch {
            show("证据服务器暂未确认，系统会重试。可以继续作答。");
            retryTimer = setTimeout(flush, retryWait);
            retryWait = Math.min(retryWait * 2, 15000);
        } finally {
            sending = false;
        }
    }

    function enqueue(clip) {
        if (clip.blob.size + queue.reduce((total, item) => total + item.blob.size, 0) > maxQueuedBytes) {
            dropped = true;
            event("queue_full");
            return;
        }
        queue.push(clip);
        void pending("readwrite", store => store.put(clip)).catch(() => { storageWarning = true; })
            .then(() => flush());
    }

    function recordSegment(type) {
        const chunks = [];
        const instance = new MediaRecorder(stream, {mimeType: type, videoBitsPerSecond: 300000, audioBitsPerSecond: 32000});
        const key = crypto.randomUUID();
        const startMs = elapsed();
        const deviceAtMs = Date.now();
        let endMs;
        instance.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
        instance.onstop = () => {
            inFlight.delete(instance);
            const blob = new Blob(chunks, {type: instance.mimeType});
            const stopMs = endMs ?? elapsed();
            if (blob.size && stopMs - startMs >= 300) {
                enqueue({key, sessionId: session.sessionId, startMs, endMs: stopMs, deviceAtMs,
                    createdAt: Date.now(), blob});
            }
            if (userPaused && !active && !inFlight.size && !queue.length && !dropped) {
                show("录制已暂停。本页已确认 " + uploaded + " 段。");
            }
        };
        instance.onerror = () => {
            inFlight.delete(instance);
            stopRecording();
            event("record_error");
            show("设备录制失败，可继续考试。");
        };
        instance.start();
        recorder = {instance, finish() {
            if (instance.state === "recording") {
                endMs = elapsed();
                instance.stop();
            }
        }};
        inFlight.set(instance, recorder);
        rollover = setTimeout(() => {
            if (!active) return;
            const previous = recorder;
            try {
                recordSegment(type);
                // Start the next encoder before closing the current one to preserve frame coverage.
                setTimeout(() => previous.finish(), 150);
            } catch {
                stopRecording();
                event("record_error");
                show("录制中断，可继续考试。");
            }
        }, session.segmentMs);
    }

    function stopRecording() {
        active = false;
        clearTimeout(rollover);
        for (const item of inFlight.values()) item.finish();
        recorder = null;
        stream?.getTracks().forEach(track => track.stop());
        stream = null;
        video.srcObject = null;
        video.hidden = true;
        start.disabled = false;
        stop.disabled = true;
        start.textContent = "继续录制";
    }

    async function register(consent) {
        const body = new URLSearchParams({consent: consent ? "1" : "0", attempt: panel.dataset.attempt});
        const csrf = panel.dataset.csrfValue || panel.querySelector("[name=csrfmiddlewaretoken]")?.value;
        body.set(panel.dataset.csrfName, csrf);
        const sent = performance.now();
        const response = await fetch(panel.dataset.sessionUrl, {
            method: "POST", body, credentials: "same-origin", signal: AbortSignal.timeout(8000),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "无法建立采集会话。");
        anchor = (sent + performance.now()) / 2 - data.elapsedMs;
        return data;
    }

    async function begin() {
        if (active || start.disabled) return;
        userPaused = false;
        start.disabled = true;
        decline.disabled = true;
        show("正在检查设备和证据服务…");
        try {
            session = await register(true);
            if (!session.token) throw new Error("该作答已结束接收。");
            selectionValue("granted");
            await restore();
            void flush();
            if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                throw new Error("当前页面无法使用音视频设备。请检查 SEB 和 HTTPS 设置。");
            }
            const type = segmentTypes.find(value => MediaRecorder.isTypeSupported(value));
            if (!type) throw new Error("当前客户端无法录制 WebM。");
            stream = await navigator.mediaDevices.getUserMedia({
                video: {width: {ideal: 320}, height: {ideal: 180}, frameRate: {ideal: 15, max: 20}},
                audio: true,
            });
            if (!stream.getAudioTracks().length || !stream.getVideoTracks().length) throw new Error("缺少一条设备轨道。");
            for (const track of stream.getTracks()) {
                track.addEventListener("ended", () => {
                    if (!active) return;
                    stopRecording();
                    event("track_ended");
                    show("设备连接中断，仍可继续考试。");
                });
            }
            video.srcObject = stream;
            video.hidden = false;
            active = true;
            recordSegment(type);
            stop.disabled = false;
            event("client_ready");
            show("设备已连接，正在录制。等待首段保存确认。");
        } catch (error) {
            stopRecording();
            event(error.name === "NotAllowedError" ? "device_denied" : "device_failed");
            show(error.name === "NotAllowedError" ? "设备权限被拒绝，仍可继续考试。"
                : (error.name === "AbortError" || error.name === "TimeoutError") ? "证据服务未响应，仍可继续考试。"
                : "暂时无法采集，仍可继续考试。" + (error.message || ""));
        }
    }

    start.addEventListener("click", begin);
    stop.addEventListener("click", () => {
        userPaused = true;
        selectionValue("paused");
        stopRecording();
        event("client_paused");
        show("录制已暂停，正在处理待传片段。");
    });
    decline.addEventListener("click", async () => {
        selectionValue("declined");
        decline.disabled = true;
        start.disabled = true;
        try {
            await register(false);
            show("已记录拒绝采集，可以继续考试。");
        } catch {
            show("已选择拒绝采集，证据服务暂未确认。可以继续考试。");
            decline.disabled = false;
        } finally {
            start.disabled = false;
        }
    });
    window.addEventListener("online", () => { event("network_restored"); void flush(); });
    window.addEventListener("offline", () => {
        event("network_lost");
        if (active) show("网络已中断，录制片段暂存在发送队列。");
    });
    window.addEventListener("pagehide", stopRecording);
    window.addEventListener("pageshow", browserEvent => {
        if (browserEvent.persisted && selectionValue() === "granted") void begin();
    });
    if (selectionValue() === "granted") {
        void begin();
    } else if (selectionValue() === "paused") {
        start.textContent = "继续录制";
        show("录制已暂停。");
    } else if (selectionValue() === "declined") {
        show("上次选择了拒绝采集。");
    }
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, {once: true});
    } else {
        init();
    }
})();

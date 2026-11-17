const player = document.querySelector("[data-replay]");
const status = document.querySelector("[data-replay-status]");
let seek = 0;
if (player) {
    player.addEventListener("loadedmetadata", () => {
        if (seek) player.currentTime = Math.min(seek, player.duration);
    });
}
document.addEventListener("click", event => {
    const clip = event.target.closest("[data-play]");
    if (clip && player) {
        seek = Number(clip.dataset.offset || 0);
        if (new URL(clip.dataset.play, location.href).href === player.src && player.readyState) {
            player.currentTime = Math.min(seek, player.duration);
        } else {
            player.src = clip.dataset.play;
        }
        status.textContent = clip.dataset.label;
        player.play().catch(() => { status.textContent += " · 点击播放器继续"; });
    }
    const revision = event.target.closest("[data-revise]");
    if (revision) {
        document.querySelector("#revision").value = revision.dataset.revise;
        document.querySelector("#decision").value = revision.dataset.decision;
        const note = document.querySelector("#note");
        note.value = revision.dataset.note;
        note.focus();
    }
});

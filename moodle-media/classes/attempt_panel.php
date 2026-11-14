<?php
namespace local_examguardianmedia;

final class attempt_panel {
    public static function add_panel(\core\hook\output\before_footer_html_generation $hook): void {
        global $PAGE;

        $cmid = (int) get_config('local_examguardianmedia', 'cmid');
        if (!$cmid || $PAGE->pagetype !== 'mod-quiz-attempt' || (int) ($PAGE->cm->id ?? 0) !== $cmid) {
            return;
        }

        $PAGE->requires->js('/local/examguardianmedia/attempt-media.js');
        $hook->add_html(<<<'HTML'
            <section id="exam-guardian-media" class="card p-3 my-3" hidden>
              <h2 class="h5">Exam Guardian 音视频测试</h2>
              <p>点击开始并授权后，检查画面和麦克风电平。测试最多 10 秒。</p>
              <p>
                <button type="button" class="btn btn-primary" data-media-start>开始测试</button>
                <button type="button" class="btn btn-secondary" data-media-stop disabled>停止</button>
              </p>
              <video width="320" height="180" data-media-video autoplay muted playsinline hidden></video>
              <label>麦克风电平 <meter data-media-level min="0" max="1" value="0"></meter></label>
              <p data-media-status role="status"></p>
            </section>
            HTML);
    }
}

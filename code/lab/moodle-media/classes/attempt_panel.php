<?php
namespace local_examguardianmedia;

final class attempt_panel {
    public static function add_panel(\core\hook\output\before_footer_html_generation $hook): void {
        global $PAGE, $USER;

        $cmid = (int) get_config('local_examguardianmedia', 'cmid');
        if (!$cmid || (int) ($PAGE->cm->id ?? 0) !== $cmid) {
            return;
        }

        if ($PAGE->pagetype === 'mod-quiz-view' && has_capability('mod/quiz:viewreports', $PAGE->context)) {
            $url = new \moodle_url('/local/examguardianmedia/index.php', ['cmid' => $cmid]);
            $hook->add_html(\html_writer::div(\html_writer::link($url, '查看本场音视频片段'), 'my-3'));
        }
        if ($PAGE->pagetype !== 'mod-quiz-attempt') {
            return;
        }

        $attempt = $PAGE->url->param('attempt');
        $location = trim((string) get_config('local_examguardianmedia', 'locationlabel'));
        if (!$attempt || !$location) {
            return;
        }

        $collection = !has_capability('mod/quiz:preview', $PAGE->context, $USER);
        $label = $collection ? '开始录制' : '开始预览';
        $notice = $collection
            ? '点击后开启摄像头和麦克风，最多录制 10 秒。看到片段编号后再翻页或交卷。片段保存到 Moodle 供有权限的教师回查。'
            : '教师预览模式。点击后开启摄像头和麦克风，最多预览 10 秒。';
        $attributes = \html_writer::attributes([
            'id' => 'exam-guardian-media',
            'class' => 'card p-3 my-3',
            'hidden' => 'hidden',
            'data-attempt' => $attempt,
            'data-upload' => $collection ? (new \moodle_url('/local/examguardianmedia/upload.php'))->out(false) : '',
            'data-sesskey' => $collection ? sesskey() : '',
        ]);
        $PAGE->requires->js('/local/examguardianmedia/attempt-media.js');
        $hook->add_html(<<<HTML
            <section{$attributes}>
              <h2 class="h5">Exam Guardian 音视频测试</h2>
              <p>{$notice}</p>
              <p>
                <button type="button" class="btn btn-primary" data-media-start>{$label}</button>
                <button type="button" class="btn btn-secondary" data-media-stop disabled>停止</button>
                <button type="button" class="btn btn-outline-secondary" data-media-retry hidden>重试保存</button>
              </p>
              <video width="320" height="180" data-media-video autoplay muted playsinline hidden></video>
              <label>麦克风电平 <meter data-media-level min="0" max="1" value="0"></meter></label>
              <p data-media-status role="status"></p>
            </section>
            HTML);
    }
}

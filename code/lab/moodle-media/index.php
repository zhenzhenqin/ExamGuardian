<?php
require_once(__DIR__ . '/../../config.php');

if (!in_array($_SERVER['REQUEST_METHOD'], ['GET', 'HEAD'], true)) {
    header('Allow: GET, HEAD');
    http_response_code(405);
    exit;
}

$cmid = required_param('cmid', PARAM_INT);
$attemptid = optional_param('attempt', 0, PARAM_INT);
$page = max(0, optional_param('page', 0, PARAM_INT));
$perpage = 20;
$cm = get_coursemodule_from_id('quiz', $cmid, 0, false, MUST_EXIST);
require_login($cm->course, false, $cm);
$context = context_module::instance($cmid);
require_capability('mod/quiz:viewreports', $context);

$url = new moodle_url('/local/examguardianmedia/index.php', ['cmid' => $cmid, 'attempt' => $attemptid]);
$PAGE->set_url($url);
$PAGE->set_context($context);
$PAGE->set_title('Exam Guardian 音视频记录');
$PAGE->set_heading(format_string($cm->name));

$conditions = ['cmid' => $cmid];
if ($attemptid > 0) {
    $conditions['attemptid'] = $attemptid;
}
$total = $DB->count_records('local_examguardianmedia_clip', $conditions);
$clips = $DB->get_records('local_examguardianmedia_clip', $conditions, 'receivedms DESC, id DESC', '*', $page * $perpage, $perpage);
$users = $clips ? $DB->get_records_list('user', 'id', array_unique(array_column($clips, 'userid'))) : [];
$zone = new DateTimeZone('Asia/Shanghai');

echo $OUTPUT->header();
echo $OUTPUT->heading('音视频记录');
echo html_writer::tag('p', '时间显示为北京时间。采集时间来自考生设备，服务器接收时间用于独立核对。地点是考场配置标签。');
echo html_writer::start_tag('form', ['action' => $url->out_omit_querystring(), 'method' => 'get', 'class' => 'mb-4']);
echo html_writer::empty_tag('input', ['type' => 'hidden', 'name' => 'cmid', 'value' => $cmid]);
echo html_writer::tag('label', '作答编号', ['for' => 'attempt-filter', 'class' => 'mr-2']);
echo html_writer::empty_tag('input', [
    'id' => 'attempt-filter', 'name' => 'attempt', 'type' => 'number',
    'min' => 1, 'value' => $attemptid ?: '', 'class' => 'mr-2',
]);
echo html_writer::tag('button', '查找', ['type' => 'submit', 'class' => 'btn btn-primary mr-2']);
echo html_writer::link(new moodle_url('/local/examguardianmedia/index.php', ['cmid' => $cmid]), '全部');
echo html_writer::end_tag('form');

if (!$clips) {
    echo $OUTPUT->notification('这一页暂无音视频片段。', 'info');
}
foreach ($clips as $clip) {
    $capture = (new DateTimeImmutable('@' . intdiv($clip->capturems, 1000)))->setTimezone($zone);
    $received = (new DateTimeImmutable('@' . intdiv($clip->receivedms, 1000)))->setTimezone($zone);
    $review = new moodle_url('/mod/quiz/review.php', ['attempt' => $clip->attemptid, 'cmid' => $cmid]);
    $media = new moodle_url('/local/examguardianmedia/clip.php', ['id' => $clip->id]);
    $name = isset($users[$clip->userid]) ? fullname($users[$clip->userid]) : '用户 #' . $clip->userid;

    echo html_writer::start_tag('article', ['class' => 'card p-3 mb-3']);
    echo $OUTPUT->heading('片段 EG-' . $clip->id, 3);
    echo html_writer::tag('p', s($name) . ' · ' . html_writer::link($review, '作答 #' . $clip->attemptid));
    echo html_writer::tag('p', '采集 ' . $capture->format('Y-m-d H:i:s') . '.' . sprintf('%03d', $clip->capturems % 1000)
        . ' · 接收 ' . $received->format('Y-m-d H:i:s') . '.' . sprintf('%03d', $clip->receivedms % 1000)
        . ' · ' . number_format($clip->durationms / 1000, 2) . ' 秒 · ' . s($clip->locationlabel));
    echo html_writer::tag('video', '', [
        'controls' => 'controls', 'preload' => 'none', 'src' => $media->out(false),
        'width' => 320, 'class' => 'mw-100', 'aria-label' => '播放片段 EG-' . $clip->id,
    ]);
    echo html_writer::tag('details', html_writer::tag('summary', '文件校验值（SHA-256）')
        . html_writer::tag('code', s($clip->sha256)));
    echo html_writer::end_tag('article');
}
echo $OUTPUT->paging_bar($total, $page, $perpage, $url);
echo $OUTPUT->footer();

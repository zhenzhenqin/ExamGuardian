<?php
require_once(__DIR__ . '/../../config.php');

use local_examguardianmedia\evidence_client;
use mod_quiz\quiz_attempt;

function eg_session_reply(int $status, array $data): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    eg_session_reply(405, ['error' => '请从作答页启动录制。']);
}
if (!isloggedin() || isguestuser() || !confirm_sesskey()) {
    eg_session_reply(403, ['error' => '登录已失效，请返回作答页。']);
}
$id = optional_param('attempt', 0, PARAM_INT);
$consent = optional_param('consent', -1, PARAM_INT);
$cmid = (int) get_config('local_examguardianmedia', 'cmid');
$record = $DB->get_record('quiz_attempts', ['id' => $id, 'userid' => $USER->id]);
if (!$record || !$cmid || !in_array($consent, [0, 1], true) || $record->preview ||
        $record->state !== quiz_attempt::IN_PROGRESS || !evidence_client::configured()) {
    eg_session_reply(403, ['error' => '该作答未启用证据采集。']);
}

try {
    $attempt = quiz_attempt::create($id);
    if ((int) $attempt->get_cm()->id !== $cmid || !has_capability('mod/quiz:attempt', $attempt->get_context())) {
        eg_session_reply(403, ['error' => '该作答未启用证据采集。']);
    }
    $student = hash_hmac('sha256', $CFG->wwwroot . ':' . $USER->id, $CFG->passwordsaltmain ??
        (string) get_config('local_examguardianmedia', 'evidencesecret'));
    \core\session\manager::write_close();
    $data = evidence_client::request('start', [
        'attemptId' => $id,
        'cmid' => $cmid,
        'quizId' => (int) $record->quiz,
        'studentRef' => $student,
        'consent' => (bool) $consent,
    ]);
    eg_session_reply(200, $data);
} catch (Throwable $problem) {
    error_log('Exam Guardian session setup: ' . $problem->getMessage());
    eg_session_reply(503, ['error' => '证据服务暂不可用。可以继续考试。']);
}

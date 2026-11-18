<?php
require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/filelib.php');

use mod_quiz\quiz_attempt;

function clip_response(int $status, array $body): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    clip_response(405, ['error' => '请使用录制面板保存。']);
}
$requestkey = optional_param('sesskey', '', PARAM_RAW);
if (!isloggedin() || isguestuser() || !$requestkey || !confirm_sesskey($requestkey)) {
    clip_response(403, ['error' => '登录已失效，请重新进入测验。']);
}

$attemptid = optional_param('attempt', 0, PARAM_INT);
$cmid = (int) get_config('local_examguardianmedia', 'cmid');
$location = trim((string) get_config('local_examguardianmedia', 'locationlabel'));
if (!$attemptid || !$cmid || $location === '' || core_text::strlen($location) > 120 ||
        !$DB->record_exists('quiz_attempts', ['id' => $attemptid, 'userid' => $USER->id])) {
    clip_response(403, ['error' => '这份答题记录未启用采集。']);
}
$attempt = quiz_attempt::create($attemptid);
$context = $attempt->get_context();
if ((int) $attempt->get_cm()->id !== $cmid || $attempt->is_preview() ||
        !has_capability('mod/quiz:attempt', $context)) {
    clip_response(403, ['error' => '这份答题记录未启用采集。']);
}
if (\local_examguardianmedia\evidence_client::enabled_for($cmid)) {
    clip_response(403, ['error' => '该测验已改用新版采集。请从作答页保存片段。']);
}

$key = optional_param('clipkey', '', PARAM_ALPHANUMEXT);
$capturevalue = optional_param('capturems', '', PARAM_RAW_TRIMMED);
$duration = optional_param('durationms', 0, PARAM_INT);
$received = (int) round(microtime(true) * 1000);
$file = $_FILES['clip'] ?? null;
if (!preg_match('/^[a-f0-9]{24}$/D', $key) || !preg_match('/^[1-9][0-9]{12}$/D', $capturevalue) ||
        $duration < 1 || $duration > 12000) {
    clip_response(400, ['error' => '片段编号或时间无效。']);
}
if (!$file || $file['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($file['tmp_name']) ||
        $file['size'] < 32 || $file['size'] > 8 * 1024 * 1024) {
    clip_response(400, ['error' => '片段为空或超过 8 MB。']);
}
$mimetype = (new finfo(FILEINFO_MIME_TYPE))->file($file['tmp_name']);
if ($mimetype !== 'video/webm' ||
        file_get_contents($file['tmp_name'], false, null, 0, 4) !== "\x1a\x45\xdf\xa3") {
    clip_response(400, ['error' => '当前采集仅支持 WebM。']);
}

$hash = hash_file('sha256', $file['tmp_name']);
$factory = \core\lock\lock_config::get_lock_factory('local_examguardianmedia');
$lock = $factory->get_lock((string) $attemptid, 5);
if (!$lock) {
    clip_response(503, ['error' => '保存繁忙，可以重试。']);
}

try {
    $existing = $DB->get_record('local_examguardianmedia_clip', ['attemptid' => $attemptid, 'clipkey' => $key]);
    if ($existing) {
        $result = $existing->sha256 === $hash
            ? [200, ['id' => (int) $existing->id]]
            : [409, ['error' => '片段编号已被不同文件使用。']];
    } else if (!$DB->record_exists('quiz_attempts', ['id' => $attemptid, 'state' => quiz_attempt::IN_PROGRESS])) {
        $result = [409, ['error' => '测验已结束。请在提交前保存片段。']];
    } else if ($DB->count_records('local_examguardianmedia_clip', ['attemptid' => $attemptid]) >= 10) {
        $result = [409, ['error' => '本次答题已保存 10 段。']];
    } else {
        $transaction = $DB->start_delegated_transaction();
        try {
            $id = $DB->insert_record('local_examguardianmedia_clip', (object) [
                'cmid' => $cmid,
                'attemptid' => $attemptid,
                'userid' => $USER->id,
                'clipkey' => $key,
                'locationlabel' => $location,
                'capturems' => (int) $capturevalue,
                'receivedms' => $received,
                'durationms' => $duration,
                'sha256' => $hash,
            ]);
            get_file_storage()->create_file_from_pathname([
                'contextid' => $context->id,
                'component' => 'local_examguardianmedia',
                'filearea' => 'clips',
                'itemid' => $id,
                'filepath' => '/',
                'filename' => 'evidence.webm',
                'mimetype' => 'video/webm',
                'userid' => $USER->id,
            ], $file['tmp_name']);
            $transaction->allow_commit();
        } catch (Throwable $exception) {
            $transaction->rollback($exception);
        }
        $result = [201, ['id' => (int) $id]];
    }
} catch (Throwable $exception) {
    error_log('Exam Guardian clip save failed: ' . $exception->getMessage());
    $result = [500, ['error' => '保存失败，可以重试。']];
} finally {
    $lock->release();
}
clip_response(...$result);

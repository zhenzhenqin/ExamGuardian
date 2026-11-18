<?php
require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/filelib.php');

if (!in_array($_SERVER['REQUEST_METHOD'], ['GET', 'HEAD'], true)) {
    header('Allow: GET, HEAD');
    http_response_code(405);
    exit;
}

$id = required_param('id', PARAM_INT);
require_login();
$clip = $DB->get_record('local_examguardianmedia_clip', ['id' => $id]);
if (!$clip) {
    send_file_not_found();
}
$cm = get_coursemodule_from_id('quiz', $clip->cmid, 0, false, MUST_EXIST);
require_login($cm->course, false, $cm);
$context = context_module::instance($cm->id);
require_capability('mod/quiz:viewreports', $context);
$file = get_file_storage()->get_file($context->id, 'local_examguardianmedia', 'clips', $id, '/', 'evidence.webm');
if (!$file) {
    send_file_not_found();
}
header('X-Content-Type-Options: nosniff');
header("Content-Security-Policy: default-src 'none'; sandbox");
send_stored_file($file, 0, 0, false, ['filename' => 'EG-' . $id . '.webm']);

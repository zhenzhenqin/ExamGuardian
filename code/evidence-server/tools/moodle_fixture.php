<?php
// Create two students, a teacher, and an ordinary-browser quiz in the lab course.
// Run only on a lab Moodle, with Moodle root and local output file as arguments.
define('CLI_SCRIPT', true);
if ($argc !== 4 || !ctype_digit($argv[2]) || !str_starts_with($argv[3], '/')) {
    fwrite(STDERR, "Usage: php moodle_fixture.php MOODLE_ROOT SOURCE_CMID ABSOLUTE_LOCAL_JSON\n");
    exit(2);
}
require $argv[1] . '/config.php';
require_once($CFG->dirroot . '/course/modlib.php');
require_once($CFG->dirroot . '/user/lib.php');
require_once($CFG->dirroot . '/mod/quiz/locallib.php');

if (!preg_match('~^http://(127\.0\.0\.1|localhost)(:\d+)?$~D', $CFG->wwwroot)) {
    throw new RuntimeException('Only a loopback lab site is supported.');
}
$source = get_coursemodule_from_id('quiz', (int) $argv[2], 0, false, MUST_EXIST);
$course = $DB->get_record('course', ['id' => $source->course], '*', MUST_EXIST);
$quiz = $DB->get_record('quiz', ['id' => $source->instance], '*', MUST_EXIST);
if (!str_contains($quiz->name, 'Exam Guardian')) {
    throw new RuntimeException('Choose an Exam Guardian lab quiz.');
}
$tx = $DB->start_delegated_transaction();
\core\session\manager::set_user(get_admin());
unset($quiz->id);
$quiz->name = 'Exam Guardian · Edge integration fixture ' . date('Ymd-Hi');
$quiz->modulename = 'quiz';
$quiz->module = (int) $source->module;
$quiz->section = 0;
$quiz->visible = 1;
$quiz->timeopen = 0;
$quiz->timeclose = 0;
$quiz->timelimit = 0;
$quiz->attempts = 0;
$quiz->quizpassword = '';
$quiz->password = '';
$quiz->browsersecurity = '-';
$quiz->seb_requiresafeexambrowser = 0;
$quiz->sebserverenabled = 0;
$quiz->intro = 'Ordinary-browser test fixture for the Exam Guardian adapter.';
$quiz->introformat = FORMAT_PLAIN;
$quiz->questionsperpage = 1;
$module = add_moduleinfo($quiz, $course);
$created = $DB->get_record('quiz', ['id' => $module->instance], '*', MUST_EXIST);
$sourcecontext = context_module::instance($source->id);
$references = $DB->get_records_sql(
    'SELECT qs.id, qr.questionbankentryid
       FROM {quiz_slots} qs
       JOIN {question_references} qr ON qr.itemid = qs.id
      WHERE qs.quizid = ? AND qr.usingcontextid = ? AND qr.component = ? AND qr.questionarea = ?
      ORDER BY qs.slot',
    [$source->instance, $sourcecontext->id, 'mod_quiz', 'slot'],
);
$slot = 0;
foreach ($references as $reference) {
    $version = $DB->get_records('question_versions', ['questionbankentryid' => $reference->questionbankentryid],
                                'version DESC', '*', 0, 1);
    if ($version) {
        quiz_add_quiz_question(reset($version)->questionid, $created, ++$slot);
    }
}
if (!$slot) {
    throw new RuntimeException('Lab quiz requires at least one source question.');
}
\mod_quiz\grade_calculator::create(\mod_quiz\quiz_settings::create($created->id))->recompute_quiz_sumgrades();
$manual = array_filter(enrol_get_instances($course->id, true), static fn($entry) => $entry->enrol === 'manual');
if (!$manual) {
    throw new RuntimeException('Lab course requires manual enrolments.');
}
$enrolment = reset($manual);
$createfixtureuser = static function (string $role, string $label) use ($CFG, $DB, $enrolment): array {
    $roleid = $DB->get_field('role', 'id', ['shortname' => $role], MUST_EXIST);
    $username = 'egfixture' . bin2hex(random_bytes(6));
    $password = 'Eg!' . bin2hex(random_bytes(14));
    $id = user_create_user((object) [
        'username' => $username, 'firstname' => 'Evidence', 'lastname' => 'Fixture ' . $label,
        'email' => $username . '@example.invalid', 'password' => $password,
        'auth' => 'manual', 'confirmed' => 1, 'mnethostid' => $CFG->mnet_localhost_id,
    ]);
    enrol_get_plugin('manual')->enrol_user($enrolment, $id, $roleid);
    return ['username' => $username, 'password' => $password];
};
$students = [$createfixtureuser('student', 'Student A'), $createfixtureuser('student', 'Student B')];
$teacher = $createfixtureuser('editingteacher', 'Teacher');
umask(0077);
if (file_put_contents($argv[3], json_encode([
    'cmid' => (int) $module->coursemodule, 'quizId' => (int) $created->id, 'students' => $students, 'teacher' => $teacher,
], JSON_THROW_ON_ERROR), LOCK_EX) === false) {
    throw new RuntimeException('Could not write the local fixture credentials.');
}
$tx->allow_commit();
echo 'Created loopback lab quiz for integration tests. Keep the credential file local.' . PHP_EOL;

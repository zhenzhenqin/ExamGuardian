<?php
namespace local_examguardianmedia;

defined('MOODLE_INTERNAL') || die();

final class observer {
    public static function attempt_ended(\core\event\base $event): void {
        if (!evidence_client::enabled_for((int) $event->contextinstanceid)) {
            return;
        }
        $task = new \local_examguardianmedia\task\finish_session();
        $task->set_component('local_examguardianmedia');
        $task->set_custom_data(['attemptId' => (int) $event->objectid, 'endedAt' => (int) $event->timecreated]);
        \core\task\manager::queue_adhoc_task($task, true);
    }
}

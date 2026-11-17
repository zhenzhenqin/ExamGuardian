<?php
namespace local_examguardianmedia\task;

defined('MOODLE_INTERNAL') || die();

final class finish_session extends \core\task\adhoc_task {
    public function get_name() {
        return 'Finish Exam Guardian evidence session';
    }

    public function execute() {
        if (\local_examguardianmedia\evidence_client::configured()) {
            \local_examguardianmedia\evidence_client::request('end', (array) $this->get_custom_data());
        }
    }
}

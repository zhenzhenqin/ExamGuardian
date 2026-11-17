<?php
defined('MOODLE_INTERNAL') || die();

function xmldb_local_examguardianmedia_upgrade(int $oldversion): bool {
    global $DB, $CFG;

    if ($oldversion < 2026111401) {
        $manager = $DB->get_manager();
        if (!$manager->table_exists('local_examguardianmedia_clip')) {
            $manager->install_from_xmldb_file($CFG->dirroot . '/local/examguardianmedia/db/install.xml');
        }
        upgrade_plugin_savepoint(true, 2026111401, 'local', 'examguardianmedia');
    }
    return true;
}

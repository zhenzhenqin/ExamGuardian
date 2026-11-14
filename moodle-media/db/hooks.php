<?php
defined('MOODLE_INTERNAL') || die();

$callbacks = [
    [
        'hook' => \core\hook\output\before_footer_html_generation::class,
        'callback' => \local_examguardianmedia\attempt_panel::class . '::add_panel',
    ],
];

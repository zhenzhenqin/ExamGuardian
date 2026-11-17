<?php
defined('MOODLE_INTERNAL') || die();

$observers = [
    [
        'eventname' => '\mod_quiz\event\attempt_submitted',
        'callback' => '\local_examguardianmedia\observer::attempt_ended',
    ],
    [
        'eventname' => '\mod_quiz\event\attempt_abandoned',
        'callback' => '\local_examguardianmedia\observer::attempt_ended',
    ],
];

<?php
namespace local_examguardianmedia;

defined('MOODLE_INTERNAL') || die();

final class evidence_client {
    public static function configured(): bool {
        return (bool) get_config('local_examguardianmedia', 'evidenceurl') &&
            (bool) get_config('local_examguardianmedia', 'evidencesecret');
    }

    public static function enabled_for(int $cmid): bool {
        if (!$cmid || !self::configured()) {
            return false;
        }
        $configured = trim((string) get_config('local_examguardianmedia', 'evidencecmids'));
        if ($configured === '') {
            return $cmid === (int) get_config('local_examguardianmedia', 'cmid');
        }
        return in_array((string) $cmid, array_map('trim', explode(',', $configured)), true);
    }

    public static function request(string $action, array $data): array {
        $base = rtrim((string) get_config('local_examguardianmedia', 'evidenceurl'), '/');
        $secret = (string) get_config('local_examguardianmedia', 'evidencesecret');
        if (!preg_match('~^https?://[^/\s]+$~D', $base) || !$secret || !in_array($action, ['start', 'end'], true)) {
            throw new \RuntimeException('Evidence endpoint is not configured.');
        }
        $handle = curl_init($base . '/internal/moodle/' . $action . '/');
        curl_setopt_array($handle, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data, JSON_THROW_ON_ERROR),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Authorization: Bearer ' . $secret],
            CURLOPT_CONNECTTIMEOUT_MS => 1500,
            CURLOPT_TIMEOUT_MS => 4000,
            CURLOPT_RETURNTRANSFER => true,
        ]);
        try {
            $body = curl_exec($handle);
            $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        } finally {
            curl_close($handle);
        }
        if (!is_string($body) || $status < 200 || $status >= 300) {
            throw new \RuntimeException('Evidence service did not acknowledge the request. Status ' . $status);
        }
        $result = json_decode($body, true, 8, JSON_THROW_ON_ERROR);
        if (!is_array($result)) {
            throw new \RuntimeException('Evidence service returned an invalid result.');
        }
        return $result;
    }
}

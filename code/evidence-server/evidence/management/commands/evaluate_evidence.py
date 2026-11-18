import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from evidence.models import SCENARIOS, AnalysisJob


def overlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def score(expected, predictions):
    candidates = []
    for i, label in enumerate(expected):
        for j, predicted in enumerate(predictions):
            duration = max(label[1], predicted[1]) - min(label[0], predicted[0])
            ratio = overlap(label, predicted) / duration
            if ratio >= 0.5:
                candidates.append((ratio, i, j))
    used_labels, used_predictions = set(), set()
    for _, label, prediction in sorted(candidates, reverse=True):
        if label not in used_labels and prediction not in used_predictions:
            used_labels.add(label)
            used_predictions.add(prediction)
    tp = len(used_labels)
    return {
        "tp": tp, "fp": len(predictions) - tp, "fn": len(expected) - tp,
        "precision": tp / len(predictions) if predictions else None,
        "recall": tp / len(expected) if expected else None,
    }


class Command(BaseCommand):
    help = "Compare a completed analysis job with manually labelled session-relative intervals."

    def add_arguments(self, parser):
        parser.add_argument("job", type=int)
        parser.add_argument("labels", type=Path)

    def handle(self, **options):
        job = AnalysisJob.objects.select_related("session").filter(
            pk=options["job"], state=AnalysisJob.State.DONE).first()
        if not job:
            raise CommandError("Choose a completed analysis job.")
        try:
            labels = json.loads(options["labels"].read_text(encoding="utf-8"))
            if labels["sessionId"] != str(job.session_id):
                raise ValueError("Labels must belong to the job's session.")
            expected = {kind: [] for kind in job.rules}
            for item in labels["events"]:
                start, end = item["startMs"], item["endMs"]
                kind = item["kind"]
                if kind not in job.rules or type(start) is not int or type(end) is not int or not 0 <= start < end:
                    raise ValueError("Invalid label kind or interval.")
                expected[kind].append((start, end))
            normal = [tuple(item) for item in labels.get("normalIntervals", [])]
            if any(len(item) != 2 or any(type(value) is not int for value in item) or
                   not 0 <= item[0] < item[1] for item in normal):
                raise ValueError("Invalid normal interval.")
            normal.sort()
            if any(a[1] > b[0] for a, b in zip(normal, normal[1:])):
                raise ValueError("Normal ranges must not overlap.")
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        flags = list(job.flags.values_list("kind", "start_ms", "end_ms"))
        by_kind = {
            kind: score(expected[kind], [(a, b) for name, a, b in flags if name == kind])
            for kind in expected
        }
        normal_ms = sum(end - start for start, end in normal)
        false_normal = sum(any(overlap((start, end), bounds) for bounds in normal) for _, start, end in flags)
        report = {"sessionId": str(job.session_id), "job": job.pk, "tool": job.vision, "versions": job.versions,
                  "ruleVersion": job.rule_version, "byKind": {SCENARIOS[kind]: result for kind, result in by_kind.items()},
                  "normalMinutes": normal_ms / 60000, "normalAlerts": false_normal,
                  "normalAlertsPerMinute": false_normal * 60000 / normal_ms if normal_ms else None}
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from evidence.models import PANEL, REVIEWER


class Command(BaseCommand):
    help = "Create the reviewer and panel groups."

    def handle(self, **options):
        for role in (REVIEWER, PANEL):
            Group.objects.get_or_create(name=role)
        self.stdout.write("Reviewer and panel groups are ready.")

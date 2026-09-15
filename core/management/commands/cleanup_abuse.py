from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AbuseBucket


class Command(BaseCommand):
    help = 'Delete expired shared quota/deduplication buckets (run hourly).'

    def handle(self, **options):
        count, _ = AbuseBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f'Deleted {count} expired buckets.')

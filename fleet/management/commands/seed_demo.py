"""Seed demo companies + fleet data. Safe for production: skips when companies exist."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed Orbit ERP demo data (skips if companies already exist)"

    def handle(self, *args, **options):
        import seed
        seed.run(skip_if_populated=True)
        self.stdout.write(self.style.SUCCESS("seed_demo finished"))

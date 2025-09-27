
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Ensure a Google SocialApp exists and is linked to the current Site, using environment variables GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET."

    def handle(self, *args, **options):
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp

        provider = "google"
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not secret:
            self.stdout.write(self.style.WARNING(
                "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set; skipping SocialApp creation."
            ))
            return

        site_id = getattr(settings, "SITE_ID", 1)
        site, created = Site.objects.get_or_create(
            id=site_id,
            defaults={"domain": "localhost:8000", "name": "Local"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Site {site_id} (domain={site.domain})"))

        app, created = SocialApp.objects.get_or_create(provider=provider, name="Google")
        app.client_id = client_id
        app.secret = secret
        app.save()

        # Ensure the app is attached to our current Site
        if site not in app.sites.all():
            app.sites.add(site)

        self.stdout.write(self.style.SUCCESS(
            f"Google SocialApp ensured for site {site.domain}. Client ID/Secret updated."
        ))


from __future__ import annotations

import csv
import io
import secrets
import string
from dataclasses import dataclass
from typing import List, Dict, Tuple

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.conf import settings

from league.models import (
    Player,
    Team,
    League,
    PlayerSeasonParticipation,
    TeamSeasonParticipation,
)

ALPHABET = string.ascii_letters + string.digits


def _gen_password(length: int = 14) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


REQUIRED_HEADERS = ["first_name", "last_name", "email", "position"]
VALID_POSITIONS = {c for c, _ in Player.POSITION_CHOICES}


@dataclass
class BulkImportResult:
    created_users: int
    existing_attached: int
    emails_sent: int
    errors: List[str]


def _normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    return {k: (v or "").strip() for k, v in row.items()}


def import_players_csv_for_team(team: Team, league: League, uploaded_file) -> BulkImportResult:
    """Validate then atomically import players for a team from CSV.

    Behavior:
    - Create or update User (role=player); set password and email only for newly created users.
    - Ensure Player exists via signals; set Player.position from CSV.
    - Ensure PlayerSeasonParticipation(team, league) exists/active.
    - Send welcome emails with credentials for newly created users after commit.
    - All-or-nothing: if any error, no DB writes and no emails.
    """
    errors: List[str] = []

    # Ensure team is active in league
    if not TeamSeasonParticipation.objects.filter(team=team, league=league).exists():
        return BulkImportResult(0, 0, 0, [f"{team.name} is not active in {league}."])

    # Read CSV
    try:
        data = uploaded_file.read().decode("utf-8-sig", errors="replace")
    except Exception:
        return BulkImportResult(0, 0, 0, ["Unable to read uploaded file. Ensure it's a CSV encoded in UTF-8."])

    reader = csv.DictReader(io.StringIO(data))
    fieldnames = reader.fieldnames or []

    # Header validation
    missing = [h for h in REQUIRED_HEADERS if h not in fieldnames]
    if missing:
        return BulkImportResult(0, 0, 0, [f"Missing columns: {', '.join(missing)}"])

    cleaned_rows: List[Tuple[int, Dict[str, str]]] = []  # (row_num, row)
    seen_emails: set[str] = set()

    for i, raw in enumerate(reader, start=2):  # start=2 because row 1 is headers
        row = _normalize_row(raw)
        # Required fields
        for h in REQUIRED_HEADERS:
            if not row.get(h):
                errors.append(f"Row {i}: '{h}' is required.")
        # Email basic checks
        email = row.get("email", "").lower()
        if email:
            if email in seen_emails:
                errors.append(f"Row {i}: duplicate email '{email}' in file.")
            seen_emails.add(email)
            if "@" not in email:
                errors.append(f"Row {i}: invalid email '{email}'.")
        # Position code
        pos = row.get("position")
        if pos and pos not in VALID_POSITIONS:
            errors.append(
                f"Row {i}: invalid position '{pos}'. Use one of: {', '.join(sorted(VALID_POSITIONS))}."
            )

        cleaned_rows.append((i, row))

    if errors:
        return BulkImportResult(0, 0, 0, errors)

    User = get_user_model()

    created_users = 0
    existing_attached = 0
    notifications: List[Tuple[str, str, str]] = []  # (email, username, plain_password)

    with transaction.atomic():
        for i, row in cleaned_rows:
            email = row["email"].lower()
            first_name = row["first_name"]
            last_name = row["last_name"]
            position = row["position"]

            user = User.objects.filter(email=email).first()
            new_user = False
            plain_pw = None

            if user is None:
                # Create new player user
                plain_pw = _gen_password()
                user = User.objects.create_user(
                    email=email,
                    password=plain_pw,
                    role="player",
                    first_name=first_name,
                    last_name=last_name,
                )
                new_user = True
                created_users += 1
            else:
                # Ensure role is player; save to trigger signal if role changed
                updated = False
                if user.role != "player":
                    user.role = "player"
                    updated = True
                # Keep names up to date if provided
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                if updated:
                    user.save()
                existing_attached += 1

            # Ensure Player exists via signal and set position
            # userprofile always exists due to signal
            profile = getattr(user, "userprofile", None)
            if profile is None:
                # Safety net: create profile if somehow missing
                # (Normally created by signal on user save)
                from users.models import UserProfile  # local import to avoid cycle
                profile = UserProfile.objects.create(user=user)

            player = profile.player
            if player is None:
                # Safety net: create player if somehow missing
                player = Player.objects.create(
                    first_name=first_name or (user.username or ""),
                    last_name=last_name or "",
                    position=position or "MF",
                )
                profile.player = player
                profile.save(update_fields=["player"])
            else:
                # Update position from CSV
                if position and player.position != position:
                    player.position = position
                    player.save(update_fields=["position"])

            # Ensure PSP exists/active
            PlayerSeasonParticipation.objects.update_or_create(
                player=player,
                team=team,
                league=league,
                defaults={"is_active": True},
            )

            # Queue welcome email only for new users
            if new_user and plain_pw:
                username = user.username or user.email
                notifications.append((user.email, username, plain_pw))

        # Send emails after commit
        login_url = reverse("login")

        def _send_all():
            for email, username, pwd in notifications:
                send_mail(
                    subject="Your League account",
                    message=(
                        f"Hi {username},\n\n"
                        f"Your account has been created.\n"
                        f"Email: {email}\n"
                        f"Password: {pwd}\n"
                        f"Login: {login_url}\n\n"
                        f"Please change your password after first login."
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[email],
                    fail_silently=False,
                )

        if notifications:
            transaction.on_commit(_send_all)

    return BulkImportResult(created_users, existing_attached, len(notifications), [])

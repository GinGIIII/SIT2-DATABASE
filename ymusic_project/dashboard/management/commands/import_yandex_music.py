import csv
import random
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dashboard.models import Artist, Album, Track, User, EventType, Event


YEAR_MIN = 2010
YEAR_MAX = 2025


def parse_year(release_raw: str | None) -> int | None:
    if not release_raw:
        return None
    s = release_raw.strip()
    if not s:
        return None
    try:
        return int(s[:4])
    except Exception:
        return None


def make_ts_for_year(year: int) -> timezone.datetime:
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    naive = datetime(year, month, day, hour, minute, 0)
    return timezone.make_aware(naive, timezone.get_current_timezone())


class Command(BaseCommand):
    help = "Import Spotify Global Music CSV into normalized DB (Artist/Album/Track/User/EventType/Event), years 2010–2025 only"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file")
        parser.add_argument("--limit", type=int, default=0, help="Limit rows (0 = no limit)")
        parser.add_argument("--reset", action="store_true", help="Delete existing data before import")

    @transaction.atomic
    def handle(self, *args, **options):
        path: str = options["csv_path"]
        limit: int = options["limit"] or 0
        do_reset: bool = bool(options["reset"])

        if do_reset:
            Event.objects.all().delete()
            Track.objects.all().delete()
            Album.objects.all().delete()
            Artist.objects.all().delete()
            User.objects.all().delete()
            EventType.objects.all().delete()
            self.stdout.write(self.style.WARNING("RESET: all dashboard data deleted."))

        listen_type, _ = EventType.objects.get_or_create(code="listen")
        demo_user, _ = User.objects.get_or_create(yandex_user_id="demo_user")

        created = {"artists": 0, "albums": 0, "tracks": 0, "events": 0}
        processed = 0
        skipped_empty = 0
        skipped_year = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            required = {"artist_name", "album_name", "track_name", "track_id"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV is missing columns: {sorted(missing)}")

            for row in reader:
                processed += 1
                if limit and processed > limit:
                    break

                artist_name = (row.get("artist_name") or "").strip()
                album_name = (row.get("album_name") or "").strip()
                track_name = (row.get("track_name") or "").strip()
                track_id = (row.get("track_id") or "").strip()

                release_raw = (row.get("album_release_date") or "").strip()
                year = parse_year(release_raw)


                if not artist_name or not album_name or not track_name or not track_id:
                    skipped_empty += 1
                    continue


                if year is None or year < YEAR_MIN or year > YEAR_MAX:
                    skipped_year += 1
                    continue


                artist, a_created = Artist.objects.get_or_create(name=artist_name)
                if a_created:
                    created["artists"] += 1


                album, al_created = Album.objects.get_or_create(
                    artist=artist,
                    title=album_name,
                    defaults={"release_year": year},
                )

                if (not al_created) and (album.release_year is None):
                    album.release_year = year
                    album.save(update_fields=["release_year"])

                if al_created:
                    created["albums"] += 1


                track, t_created = Track.objects.get_or_create(
                    yandex_track_id=track_id,
                    defaults={"album": album, "title": track_name},
                )

                if (not t_created) and (track.album_id != album.id):
                    track.album = album
                    track.save(update_fields=["album"])

                if t_created:
                    created["tracks"] += 1


                explicit_raw = (row.get("explicit") or "").strip().lower()
                is_explicit = explicit_raw in {"1", "true", "t", "yes", "y"}


                Event.objects.create(
                    user=demo_user,
                    track=track,
                    event_type=listen_type,
                    ts=make_ts_for_year(year),
                    is_organic=(not is_explicit),
                )
                created["events"] += 1

        self.stdout.write(self.style.SUCCESS("IMPORT FINISHED ✅"))
        self.stdout.write(f"processed rows:   {processed}")
        self.stdout.write(f"skipped empty:    {skipped_empty}")
        self.stdout.write(f"skipped by year:  {skipped_year}  (only {YEAR_MIN}–{YEAR_MAX} kept)")
        for k, v in created.items():
            self.stdout.write(f"{k}: {v}")

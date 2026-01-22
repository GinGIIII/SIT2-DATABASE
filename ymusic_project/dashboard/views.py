from __future__ import annotations

from django.db.models import Count, Q
from django.db.models.functions import ExtractYear
from django.shortcuts import render

from .models import Album, Artist, Event, EventType, Track, User

# Аналитический период исследования ( pod yadnex music )
YEAR_MIN = 2010
YEAR_MAX = 2025


def index(request):
    # Альбомы строго по диапазону (None автоматом отсекается)
    albums_qs = (
        Album.objects.select_related("artist")
        .filter(release_year__gte=YEAR_MIN, release_year__lte=YEAR_MAX)
    )

    # Треки только те, у которых альбом в диапазоне
    tracks_qs = (
        Track.objects.select_related("album", "album__artist")
        .filter(album__release_year__gte=YEAR_MIN, album__release_year__lte=YEAR_MAX)
    )

    # Артисты, у которых есть альбомы в диапазоне
    artists_qs = (
        Artist.objects.filter(album__release_year__gte=YEAR_MIN, album__release_year__lte=YEAR_MAX)
        .distinct()
    )

    # События: год берём из ts и фильтруем 2010–2025
    events_base = (
        Event.objects.select_related("user", "track", "event_type", "track__album", "track__album__artist")
        .annotate(y=ExtractYear("ts"))
        .filter(y__gte=YEAR_MIN, y__lte=YEAR_MAX)
    )

    # Витринные таблицы (можно менять лимиты)
    artists = artists_qs.order_by("name")[:200]
    albums = albums_qs.order_by("artist__name", "title")[:200]
    tracks = tracks_qs.order_by("title")[:200]
    users = User.objects.all().order_by("yandex_user_id")[:50]
    events = events_base.order_by("-ts")[:300]

    # Статистика (строго по диапазону)
    known_flag = events_base.filter(is_organic__isnull=False).count()
    organic_cnt = events_base.filter(is_organic=True).count()
    organic_share = (organic_cnt / known_flag) if known_flag else None

    stats = {
        "year_min": YEAR_MIN,
        "year_max": YEAR_MAX,
        "artists_count": artists_qs.count(),
        "albums_count": albums_qs.count(),
        "tracks_count": tracks_qs.count(),
        "users_count": User.objects.count(),
        "events_count": events_base.count(),
        "organic_share": organic_share,
    }

    # Типы событий — показываем все, даже если 0
    events_by_type = (
        EventType.objects.annotate(
            cnt=Count(
                "event",
                filter=Q(event__ts__year__gte=YEAR_MIN, event__ts__year__lte=YEAR_MAX),
            )
        )
        .values("id", "code", "cnt")
        .order_by("-cnt", "code")
    )
    events_by_type_rows = list(events_by_type)

    # ТОП треков по событиям — строго диапазон
    top_tracks = (
        events_base.values("track__album__artist__name", "track__title")
        .annotate(listen_count=Count("id"))
        .order_by("-listen_count", "track__album__artist__name", "track__title")[:50]
    )
    top_tracks_rows = [
        {
            "artist": r["track__album__artist__name"],
            "title": r["track__title"],
            "listen_count": r["listen_count"],
        }
        for r in top_tracks
    ]

    # События по годам — выводим ВСЕ 2010..2025, даже если 0
    by_year_raw = events_base.values("y").annotate(cnt=Count("id"))
    by_year_map = {r["y"]: r["cnt"] for r in by_year_raw}
    events_by_year = [{"y": y, "cnt": by_year_map.get(y, 0)} for y in range(YEAR_MIN, YEAR_MAX + 1)]

    return render(
        request,
        "index.jinja",
        {
            "stats": stats,
            "artists": artists,
            "albums": albums,
            "tracks": tracks,
            "users": users,
            "events": events,
            "events_by_type": events_by_type_rows,
            "top_tracks": top_tracks_rows,
            "events_by_year": events_by_year,
        },
    )

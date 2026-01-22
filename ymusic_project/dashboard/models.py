from django.db import models


class Artist(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    release_year = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("artist", "title")

    def __str__(self) -> str:
        return f"{self.artist} — {self.title}"


class Track(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="tracks")
    title = models.CharField(max_length=255)
    yandex_track_id = models.CharField(max_length=128, unique=True)

    def __str__(self) -> str:
        return f"{self.album.artist} — {self.title}"


class User(models.Model):
    yandex_user_id = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.yandex_user_id


class EventType(models.Model):
    code = models.CharField(max_length=64, unique=True)

    def __str__(self) -> str:
        return self.code


class Event(models.Model):
    ts = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="events")
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    is_organic = models.BooleanField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.ts} {self.user} {self.event_type} {self.track}"

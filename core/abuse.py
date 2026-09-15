"""Atomic fixed-window quotas shared by all workers, on SQLite and PostgreSQL."""
import hashlib
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from .models import AbuseBucket


def _key(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def reserve(key, limit, seconds):
    """Reserve one attempt. False means denied; failed attempts keep their slot.

    Conditional UPDATE makes admission atomic without read/increment races.
    Expired rows are recycled; cleanup_abuse removes unused expired rows.
    """
    now = timezone.now()
    expiry = now + timedelta(seconds=seconds)
    rows = AbuseBucket.objects.filter(pk=_key(key))
    rows.filter(expires_at__lte=now).update(hits=0, expires_at=expiry)
    AbuseBucket.objects.get_or_create(pk=_key(key), defaults={'expires_at': expiry})
    return bool(rows.filter(expires_at__gt=now, hits__lt=limit).update(hits=F('hits') + 1))


def exceeded(key, limit):
    return AbuseBucket.objects.filter(
        pk=_key(key), expires_at__gt=timezone.now(), hits__gte=limit,
    ).exists()

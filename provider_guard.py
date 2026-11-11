"""Session-scoped, bounded catalogue cache and provider cooldowns.

No disk persistence or background polling. This is a UI protection layer,
not a way to bypass provider restrictions or quotas.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

CACHE_TTL_SECONDS = 6 * 3600
DEFAULT_429_SECONDS = 3600
DEFAULT_403_SECONDS = 24 * 3600
MAX_COOLDOWN_SECONDS = 24 * 3600
MAX_CACHE_ITEMS = 100


def utcnow():
    return datetime.now(timezone.utc)


def retry_seconds(value, now=None):
    now = now or utcnow()
    if not value:
        return None
    try:
        return max(0, int(value.strip()))
    except (ValueError, AttributeError):
        try:
            target = parsedate_to_datetime(value)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return max(0, int((target - now).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            return None


class ProviderGuard:
    def __init__(self):
        self.cache = {}
        self.cooldowns = {}
        self.events = []

    def _log(self, provider, outcome, status=None, now=None):
        self.events.append({'at_utc': (now or utcnow()).isoformat(), 'provider': provider,
                            'outcome': outcome, 'http_status': status})
        self.events = self.events[-100:]

    def remaining(self, provider, now=None):
        now = now or utcnow()
        until = self.cooldowns.get(provider)
        return max(0, int((until - now).total_seconds())) if until else 0

    def get_cached(self, provider, barcode, now=None):
        now = now or utcnow()
        entry = self.cache.get((provider, barcode))
        if entry and (now - entry[0]).total_seconds() < CACHE_TTL_SECONDS:
            self._log(provider, 'cache_hit', now=now)
            return dict(entry[1])
        if entry:
            del self.cache[(provider, barcode)]
        return None

    def record_success(self, provider, barcode, result, now=None):
        now = now or utcnow()
        if len(self.cache) >= MAX_CACHE_ITEMS and (provider, barcode) not in self.cache:
            oldest = min(self.cache, key=lambda k: self.cache[k][0])
            del self.cache[oldest]
        self.cache[(provider, barcode)] = (now, dict(result))
        self.cooldowns.pop(provider, None)
        self._log(provider, 'success', 200, now)

    def record_error(self, provider, error, now=None):
        now = now or utcnow()
        status = getattr(error, 'status', None)
        if status in (403, 429):
            wait = retry_seconds(getattr(error, 'retry_after', None), now)
            if wait is None:
                wait = DEFAULT_403_SECONDS if status == 403 else DEFAULT_429_SECONDS
            self.cooldowns[provider] = now + timedelta(seconds=min(MAX_COOLDOWN_SECONDS, wait))
        self._log(provider, 'request_failed', status, now)

    def fetch(self, provider, barcode, lookup, now=None):
        now = now or utcnow()
        cached = self.get_cached(provider, barcode, now)
        if cached is not None:
            return cached, 'cached'
        wait = self.remaining(provider, now)
        if wait:
            self._log(provider, 'cooldown_block', now=now)
            raise RuntimeError(f'{provider}: requests paused for approximately {wait} more seconds; no API request sent.')
        try:
            result = lookup(barcode, provider)
        except Exception as exc:
            self.record_error(provider, exc, now)
            raise
        self.record_success(provider, barcode, result, now)
        return result, 'live'

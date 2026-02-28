"""Advanced response caching for freellm_chat."""
from __future__ import annotations

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from collections import OrderedDict

_LOGGER = logging.getLogger(__name__)


class ResponseCache:
    """Advanced cache for LLM responses with statistics."""

    def __init__(
        self, 
        max_age_seconds: int = 300,
        max_entries: int = 200,
        enable_stats: bool = True
    ) -> None:
        """Initialize the cache."""
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_age = timedelta(seconds=max_age_seconds)
        self._max_entries = max_entries
        self._enable_stats = enable_stats
        
        # Statistiken
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_saved_time': 0.0,
            'created': datetime.now()
        }

    def _generate_key(self, prompt: str, user_input: str) -> str:
        """Generate a cache key from prompt and input."""
        # Normalisiere Input
        normalized_input = user_input.lower().strip()
        # Nur Hash vom Prompt (kann lang sein)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        # Kombiniere
        combined = f"{prompt_hash}||{normalized_input}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, prompt: str, user_input: str) -> str | None:
        """Get cached response if available and not expired."""
        key = self._generate_key(prompt, user_input)
        
        if key not in self._cache:
            self._stats['misses'] += 1
            return None
        
        entry = self._cache[key]
        age = datetime.now() - entry['timestamp']
        
        if age > self._max_age:
            # Cache abgelaufen
            del self._cache[key]
            self._stats['misses'] += 1
            self._stats['evictions'] += 1
            return None
        
        # Cache-Hit
        self._stats['hits'] += 1
        self._stats['total_saved_time'] += entry.get('response_time', 1.0)
        
        # Move to end (LRU)
        self._cache.move_to_end(key)
        
        _LOGGER.debug(f"Cache HIT for: {user_input[:30]}...")
        return entry['response']

    def set(
        self, 
        prompt: str, 
        user_input: str, 
        response: str,
        response_time: float = 1.0
    ) -> None:
        """Store a response in cache."""
        key = self._generate_key(prompt, user_input)
        
        self._cache[key] = {
            'response': response,
            'timestamp': datetime.now(),
            'response_time': response_time,
            'user_input': user_input[:100],  # Für Debugging
        }
        
        # Cleanup wenn zu viele Einträge
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)  # Entferne älteste
            self._stats['evictions'] += 1
        
        _LOGGER.debug(f"Cache SET for: {user_input[:30]}...")

    def invalidate(self, pattern: str | None = None) -> int:
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        
        to_remove = []
        for key, entry in self._cache.items():
            if pattern.lower() in entry.get('user_input', '').lower():
                to_remove.append(key)
        
        for key in to_remove:
            del self._cache[key]
        
        return len(to_remove)

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        now = datetime.now()
        to_remove = []
        
        for key, entry in self._cache.items():
            if now - entry['timestamp'] > self._max_age:
                to_remove.append(key)
        
        for key in to_remove:
            del self._cache[key]
            self._stats['evictions'] += 1
        
        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        now = datetime.now()
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Zähle gültige Einträge
        valid_entries = sum(
            1 for e in self._cache.values() 
            if now - e['timestamp'] <= self._max_age
        )
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self._cache) - valid_entries,
            'max_entries': self._max_entries,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'evictions': self._stats['evictions'],
            'saved_time': f"{self._stats['total_saved_time']:.1f}s",
            'cache_age': str(now - self._stats['created']).split('.')[0],
            'max_age_seconds': self._max_age.total_seconds(),
        }

    def get_recent_queries(self, limit: int = 10) -> list[dict]:
        """Get most recent cached queries."""
        entries = []
        for key, entry in reversed(self._cache.items()):
            if len(entries) >= limit:
                break
            entries.append({
                'query': entry.get('user_input', 'N/A'),
                'age': str(datetime.now() - entry['timestamp']).split('.')[0],
                'response_preview': entry['response'][:50] + '...' if len(entry['response']) > 50 else entry['response']
            })
        return entries

    def clear(self) -> None:
        """Clear the entire cache and reset stats."""
        self._cache.clear()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_saved_time': 0.0,
            'created': datetime.now()
        }
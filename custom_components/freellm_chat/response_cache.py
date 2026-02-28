"""Advanced response caching for freellm_chat."""
from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any
from collections import OrderedDict

_LOGGER = logging.getLogger(__name__)


class ResponseCache:
    """Advanced cache for LLM responses and query results with statistics."""

    def __init__(
        self, 
        max_age_seconds: int = 300,
        max_entries: int = 200,
        enable_stats: bool = True
    ) -> None:
        """Initialize the cache.
        
        Args:
            max_age_seconds: How long cache entries are valid (default: 5 minutes)
            max_entries: Maximum number of entries to store (default: 200)
            enable_stats: Whether to collect statistics (default: True)
        """
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

    def _make_key(self, prefix: str, key: str) -> str:
        """Create a normalized cache key.
        
        Args:
            prefix: Category prefix (e.g., 'result', 'llm', 'query')
            key: The actual key (e.g., user input text)
            
        Returns:
            MD5 hash of the normalized key
        """
        # Normalisiere den Key (lowercase, ohne extra Spaces)
        normalized = key.lower().strip()
        
        # Kombiniere mit Prefix
        combined = f"{prefix}:{normalized}"
        
        # Hash für konsistente Länge
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, prefix: str, key: str) -> str | None:
        """Get cached value if available and not expired.
        
        Args:
            prefix: Category prefix
            key: The key to look up
            
        Returns:
            Cached value if found and valid, None otherwise
        """
        cache_key = self._make_key(prefix, key)
        
        # Cache Miss
        if cache_key not in self._cache:
            if self._enable_stats:
                self._stats['misses'] += 1
            _LOGGER.debug(f"Cache MISS [{prefix}]: {key[:40]}...")
            return None
        
        entry = self._cache[cache_key]
        age = datetime.now() - entry['timestamp']
        
        # Abgelaufen
        if age > self._max_age:
            del self._cache[cache_key]
            if self._enable_stats:
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
            _LOGGER.debug(f"Cache EXPIRED [{prefix}]: {key[:40]}... (age: {age.total_seconds():.1f}s)")
            return None
        
        # Cache Hit
        if self._enable_stats:
            self._stats['hits'] += 1
            self._stats['total_saved_time'] += entry.get('saved_time', 1.0)
        
        # Move to end (LRU - Least Recently Used)
        self._cache.move_to_end(cache_key)
        
        _LOGGER.debug(f"Cache HIT [{prefix}]: {key[:40]}... (age: {age.total_seconds():.1f}s)")
        return entry['value']

    def set(
        self, 
        prefix: str, 
        key: str, 
        value: str,
        saved_time: float = 1.0
    ) -> None:
        """Store a value in cache.
        
        Args:
            prefix: Category prefix
            key: The key to store under
            value: The value to cache
            saved_time: Estimated time saved by caching (for stats)
        """
        cache_key = self._make_key(prefix, key)
        
        # Speichere Entry
        self._cache[cache_key] = {
            'value': value,
            'timestamp': datetime.now(),
            'saved_time': saved_time,
            'key_preview': key[:100],  # Für Debugging
            'prefix': prefix
        }
        
        _LOGGER.debug(f"Cache SET [{prefix}]: {key[:40]}...")
        
        # Cleanup wenn zu viele Einträge (LRU - entferne älteste)
        while len(self._cache) > self._max_entries:
            removed_key, removed_entry = self._cache.popitem(last=False)
            if self._enable_stats:
                self._stats['evictions'] += 1
            _LOGGER.debug(f"Cache EVICT [{removed_entry.get('prefix', '?')}]: {removed_entry.get('key_preview', '?')[:40]}...")

    def invalidate(self, pattern: str | None = None, prefix: str | None = None) -> int:
        """Invalidate cache entries matching pattern or prefix.
        
        Args:
            pattern: Text pattern to match in original keys (case-insensitive)
            prefix: Only invalidate entries with this prefix
            
        Returns:
            Number of invalidated entries
        """
        if pattern is None and prefix is None:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            _LOGGER.info(f"Cache cleared: {count} entries removed")
            return count
        
        to_remove = []
        
        for cache_key, entry in self._cache.items():
            should_remove = False
            
            # Check prefix
            if prefix and entry.get('prefix') == prefix:
                should_remove = True
            
            # Check pattern in original key
            if pattern and pattern.lower() in entry.get('key_preview', '').lower():
                should_remove = True
            
            if should_remove:
                to_remove.append(cache_key)
        
        # Remove matched entries
        for cache_key in to_remove:
            del self._cache[cache_key]
        
        if to_remove:
            _LOGGER.info(f"Cache invalidated: {len(to_remove)} entries removed (pattern: {pattern}, prefix: {prefix})")
        
        return len(to_remove)

    def cleanup_expired(self) -> int:
        """Remove all expired entries.
        
        Returns:
            Number of removed entries
        """
        now = datetime.now()
        to_remove = []
        
        for cache_key, entry in self._cache.items():
            age = now - entry['timestamp']
            if age > self._max_age:
                to_remove.append(cache_key)
        
        # Remove expired entries
        for cache_key in to_remove:
            del self._cache[cache_key]
            if self._enable_stats:
                self._stats['evictions'] += 1
        
        if to_remove:
            _LOGGER.info(f"Cache cleanup: {len(to_remove)} expired entries removed")
        
        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self._enable_stats:
            return {'stats_enabled': False}
        
        now = datetime.now()
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Zähle gültige Einträge
        valid_entries = sum(
            1 for e in self._cache.values() 
            if now - e['timestamp'] <= self._max_age
        )
        
        # Berechne durchschnittliches Alter
        if self._cache:
            ages = [
                (now - e['timestamp']).total_seconds() 
                for e in self._cache.values()
            ]
            avg_age = sum(ages) / len(ages)
        else:
            avg_age = 0
        
        return {
            # Größe
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self._cache) - valid_entries,
            'max_entries': self._max_entries,
            'usage_percent': round(len(self._cache) / self._max_entries * 100, 1),
            
            # Performance
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.1f}%",
            'evictions': self._stats['evictions'],
            
            # Zeiten
            'total_saved_time_seconds': round(self._stats['total_saved_time'], 1),
            'avg_entry_age_seconds': round(avg_age, 1),
            'max_age_seconds': self._max_age.total_seconds(),
            'cache_age': str(now - self._stats['created']).split('.')[0],
            
            # Status
            'stats_enabled': True
        }

    def get_recent_entries(self, limit: int = 10, prefix: str | None = None) -> list[dict]:
        """Get most recent cached entries.
        
        Args:
            limit: Maximum number of entries to return
            prefix: Only return entries with this prefix (optional)
            
        Returns:
            List of recent cache entries with metadata
        """
        entries = []
        
        for cache_key, entry in reversed(self._cache.items()):
            # Filter by prefix if specified
            if prefix and entry.get('prefix') != prefix:
                continue
            
            if len(entries) >= limit:
                break
            
            age = datetime.now() - entry['timestamp']
            
            entries.append({
                'prefix': entry.get('prefix', 'unknown'),
                'key': entry.get('key_preview', 'N/A')[:50],
                'age_seconds': round(age.total_seconds(), 1),
                'value_preview': str(entry.get('value', ''))[:100]
            })
        
        return entries

    def get_entries_by_prefix(self) -> dict[str, int]:
        """Get count of entries grouped by prefix.
        
        Returns:
            Dictionary mapping prefix to count
        """
        by_prefix = {}
        
        for entry in self._cache.values():
            prefix = entry.get('prefix', 'unknown')
            by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
        
        return by_prefix

    def clear(self) -> None:
        """Clear the entire cache and reset statistics."""
        count = len(self._cache)
        self._cache.clear()
        
        # Reset stats
        if self._enable_stats:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'total_saved_time': 0.0,
                'created': datetime.now()
            }
        
        _LOGGER.info(f"Cache completely cleared: {count} entries removed, stats reset")

    def get_memory_usage_estimate(self) -> dict[str, Any]:
        """Get estimated memory usage of the cache.
        
        Returns:
            Dictionary with memory usage estimates
        """
        import sys
        
        total_bytes = 0
        
        for cache_key, entry in self._cache.items():
            # Schätze Größe des Keys
            total_bytes += sys.getsizeof(cache_key)
            
            # Schätze Größe der Values
            total_bytes += sys.getsizeof(entry.get('value', ''))
            total_bytes += sys.getsizeof(entry.get('key_preview', ''))
            total_bytes += 100  # Overhead für dict, timestamp, etc.
        
        return {
            'total_bytes': total_bytes,
            'total_kb': round(total_bytes / 1024, 2),
            'total_mb': round(total_bytes / 1024 / 1024, 2),
            'avg_bytes_per_entry': round(total_bytes / len(self._cache), 2) if self._cache else 0
        }

    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)

    def __repr__(self) -> str:
        """Return string representation of cache."""
        stats = self.get_stats()
        return f"ResponseCache(entries={len(self._cache)}, hit_rate={stats.get('hit_rate', 'N/A')})"
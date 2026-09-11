import { CacheEntry, LRUCacheOptions } from "./types";

/**
 * High-performance, strongly typed LRU Cache with TTL eviction support.
 * Uses Map insertion ordering to guarantee O(1) reads, updates, and LRU eviction.
 */
export class LRUCache<K, V> {
  private readonly maxSize: number;
  private readonly ttlMs: number;
  private readonly map = new Map<K, CacheEntry<V>>();

  constructor(options: LRUCacheOptions) {
    this.maxSize = Math.max(1, options.maxSize);
    this.ttlMs = Math.max(0, options.ttlMs);
  }

  get(key: K): V | undefined {
    const entry = this.map.get(key);
    if (!entry) {
      return undefined;
    }

    const now = Date.now();
    if (this.ttlMs > 0 && now - entry.createdAt > this.ttlMs) {
      this.map.delete(key);
      return undefined;
    }

    entry.lastAccessedAt = now;
    // Move to MRU position
    this.map.delete(key);
    this.map.set(key, entry);
    return entry.data;
  }

  has(key: K): boolean {
    return this.get(key) !== undefined;
  }

  set(key: K, data: V): void {
    const now = Date.now();
    if (this.map.has(key)) {
      this.map.delete(key);
    } else if (this.map.size >= this.maxSize) {
      // Evict oldest (least recently used)
      const oldestKey = this.map.keys().next().value;
      if (oldestKey !== undefined) {
        this.map.delete(oldestKey);
      }
    }

    this.map.set(key, {
      data,
      createdAt: now,
      lastAccessedAt: now,
    });
  }

  delete(key: K): boolean {
    return this.map.delete(key);
  }

  clear(): void {
    this.map.clear();
  }

  size(): number {
    return this.map.size;
  }

  entries(): Array<[K, V]> {
    const validEntries: Array<[K, V]> = [];
    const now = Date.now();
    for (const [key, entry] of Array.from(this.map.entries())) {
      if (this.ttlMs > 0 && now - entry.createdAt > this.ttlMs) {
        this.map.delete(key);
      } else {
        validEntries.push([key, entry.data]);
      }
    }
    return validEntries;
  }

  values(): V[] {
    return this.entries().map(([, value]) => value);
  }
}

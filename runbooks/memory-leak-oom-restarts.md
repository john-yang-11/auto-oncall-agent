# Runbook: Memory leak causing OOM restarts

## Symptoms
- Process memory usage climbs steadily over hours/days rather than staying flat.
- Service restarts (OOMKilled, or process crash + supervisor restart) recur on a
  roughly periodic cycle.
- Brief error spikes coincide with each restart, then recover.

## Likely causes
- An unbounded in-memory cache or list that's never evicted/cleared.
- A subscription/listener/callback registered repeatedly without being
  unregistered (common in long-lived background threads).
- Large objects (request bodies, query results) retained via a closure or
  global reference longer than needed.

## Diagnosis steps
1. Check the memory-usage graph for a steady upward trend, not a single spike.
2. Correlate the restart cadence with deploy history to see if it started after
   a specific change.
3. Take a heap snapshot (or add periodic memory logging) to find what's growing.

## Mitigation
- Bound any unbounded cache/collection with a max size or TTL-based eviction.
- Ensure listeners/threads are properly cleaned up on shutdown or per-request.
- Add a memory-usage alert well below the OOM threshold to catch this earlier.

## Owner
On-call backend engineer.

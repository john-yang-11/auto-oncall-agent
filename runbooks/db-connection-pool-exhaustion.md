# Runbook: Database connection pool exhaustion

## Symptoms
- Requests hang or time out under load rather than failing fast.
- Latency (p95/p99) climbs sharply while error rate rises more slowly.
- Logs show "connection pool exhausted" / "timeout waiting for connection" errors.

## Likely causes
- Traffic growth outpacing the configured pool size.
- A connection leak: code path that acquires a connection but doesn't release it
  on an error path.
- A slow query holding connections longer than expected, starving the pool.

## Diagnosis steps
1. Check current pool utilization vs configured max size.
2. Look for a slow query or a spike in query duration around the same time.
3. Grep recent deploys for changes to connection handling (`with conn:` blocks,
   try/finally around connection release, new ORM session usage).

## Mitigation
- Increase pool size as a stopgap if there's headroom on the DB itself.
- Patch any connection leak (ensure release happens in a `finally` block).
- Add a query timeout so a single slow query can't monopolize a connection.

## Owner
On-call backend engineer / database on-call.

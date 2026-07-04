# Runbook: Slow responses (latency regression) after a deploy

## Symptoms
- Latency (p50/p95) increases noticeably after a deploy, without a corresponding
  spike in error rate.
- No new errors in logs — the service is "correct but slow."

## Likely causes
- A newly introduced synchronous call that used to be async/cached (e.g. an
  external API call added to a hot path).
- A missing index after a schema change, causing a query to full-scan.
- A new dependency or middleware adding per-request overhead (e.g. verbose
  logging, extra serialization).

## Diagnosis steps
1. Compare latency percentiles immediately before/after the suspected deploy.
2. Profile or trace a slow request to find which call/step regressed.
3. Diff the suspected deploy for new blocking calls, new middleware, or schema
   changes.

## Mitigation
- Roll back if the regression is severe and the cause isn't immediately obvious.
- Add caching, an index, or async execution for the newly slow step.
- Add a latency-based alert threshold so this class of regression pages sooner
  next time.

## Owner
On-call backend engineer.

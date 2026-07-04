# Runbook: Elevated 5xx on the redirect endpoint (`GET /<code>`)

## Symptoms
- Error rate on `GET /<code>` spikes well above baseline shortly after a deploy.
- Logs show unhandled exceptions (KeyError, AttributeError) inside `store.get()` or
  similar lookup calls, rather than clean 404s.
- Users report shortened links "breaking" a few seconds to minutes after creation,
  not immediately.

## Likely causes
- A recent change to link expiration / cleanup logic. Common failure mode: a unit
  mismatch between how an expiry timestamp is *stored* (e.g. seconds since epoch)
  and how it is *compared* (e.g. milliseconds since epoch), causing entries to be
  treated as expired almost immediately after creation.
- A lookup path that used to gracefully handle "not found" (e.g. `dict.get(key)`)
  was refactored to assume the key always exists (e.g. `dict[key]`), turning a
  routine miss into an unhandled exception.

## Diagnosis steps
1. Check when the error rate started climbing; compare against the deploy log.
2. Pull the diff of the most recent deploy(s) before the spike. Look specifically
   at any change touching expiration, caching, or cleanup logic.
3. Reproduce locally: create a link with a long TTL, wait a few seconds past any
   background cleanup interval, and attempt to fetch it. If it fails immediately,
   the expiry clock is very likely miscalibrated.

## Mitigation
- Roll back the offending deploy if the bad commit is confirmed.
- Short-term patch: restore `.get()`-style lookups with an explicit "not found"
  branch so failures degrade to 404 instead of 500 while the root cause is fixed.
- Fix the unit mismatch in the expiry comparison (ensure both sides use the same
  unit — seconds or milliseconds, not one of each).

## Owner
On-call backend engineer for the link-shortening service.

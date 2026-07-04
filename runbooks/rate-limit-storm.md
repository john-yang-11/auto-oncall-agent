# Runbook: Client hitting rate limits / 429 storm

## Symptoms
- Sharp rise in 429 (Too Many Requests) responses on one or a few endpoints.
- Traffic volume from a small number of client IPs or API keys is disproportionate.
- Overall error rate rises, but the service's own health checks stay green.

## Likely causes
- A misbehaving client retrying aggressively without backoff.
- A newly deployed rate-limit config that's too strict for legitimate traffic.
- A bug in a client integration causing it to loop/retry a failing request.

## Diagnosis steps
1. Break down 429s by client ID / IP / API key to find the dominant source.
2. Check whether the rate-limit thresholds changed in a recent deploy.
3. Contact the client owner if it's an internal service; check for a retry loop.

## Mitigation
- Temporarily raise the limit for the affected client while the root cause is
  fixed, if the traffic looks legitimate.
- Ask the client to add exponential backoff and jitter to retries.
- Revert the rate-limit config change if it was the trigger.

## Owner
On-call backend engineer / API platform team.

# Postmortem: Checkout Server Error Rate Spike

**Date:** 2026-06-19
**Service:** checkout
**Severity:** Critical
**Status:** Resolved

## Summary

Checkout started returning server errors (HTTP 500) on about 25% of
requests, well above our 1% target. This was caused by a failure I added on
purpose to test whether the system would correctly detect and help diagnose
a real error spike.

## Impact

- Around 25% of checkout requests failed outright
- The error rate target (under 1%) was breached for the length of the test
- Failed requests stopped immediately, before reaching catalogue or
  notifications

## Timeline

| Time | Event |
|---|---|
| T+0:00 | Error simulation added to checkout and deployed |
| T+0:00 | Sent test traffic to checkout |
| T+0:30 | Dashboard showed error rate spiking to ~25% |
| T+2:00 | Error rate alert switched from "pending" to "firing" |
| T+3:00 | Checked Jaeger for failed traces |
| T+4:00 | Checked logs in Loki using the trace ID of a failed request |
| T+5:00 | Removed the error simulation and deployed the fix |
| T+6:00 | Error rate back to normal, alert cleared |

## Detection

The dashboard's error rate panel showed a clear spike, well above the 1%
target. After the condition held for 2 minutes, the alert moved from
"pending" to "firing", confirming this was a sustained issue.

## Diagnosis

I filtered Jaeger to show only failed requests. Unlike a slow request, these
traces only had a single step in them, no calls to catalogue or
notifications at all. That told me straight away that checkout was failing
right at the start, before it even tried to reach either of the other
services. I didn't need to check catalogue or notifications at all to rule
them out. The trace shape alone showed that.

Checking the logs for one of the failed requests in Loki showed:

```
Processing checkout | trace_id=d077c3329498a2c36c3bf91a78aa9399| product_id=4
Simulated server error | trace_id=d077c3329498a2c36c3bf91a78aa9399 | product_id=4
```

There was no "product lookup" or "notification sent" line for this request,
which confirmed it never got that far. The log also gave me the actual
error message, which the trace alone doesn't show, and that's the extra detail
logs add on top of what tracing tells you.

## Root Cause

A failure was deliberately added to checkout's code to confirm that error
detection, tracing, and logging would correctly catch and help explain a
real error spike.

## Resolution

Removed the simulated failure and redeployed through the CI/CD pipeline.
Error rate returned to normal within one deployment, and the alert cleared
on its own.

## Prevention / Follow-up

- A failed request with no downstream calls was easy to spot in Jaeger and
  immediately pointed to checkout as the source. Useful pattern to
  remember for any real error spike going forward.
- Logs gave the one thing tracing couldn't, the actual error message, 
  which confirms why checking logs alongside traces matters, especially
  for failures rather than slowdowns.
- Alert notifications (e.g. sending to email or Teams) aren't set up yet, 
  for now I checked alerts manually in the dashboard. This is a planned next
  step, same as noted in the latency incident.
- Confirmed that normal client errors (like an invalid product ID) don't
  trigger this alert, only real server failures do, which is working as
  intended.
# Postmortem: Checkout Latency Spike

**Date:** 2026-06-19
**Service:** checkout
**Severity:** Warning
**Status:** Resolved

## Summary

Checkout response times went above our 300ms target, peaking at about 1.48
seconds. This was caused by a delay I added on purpose to test whether the
alerting and monitoring setup would actually catch a slowdown.

## Impact

- Most checkout requests took noticeably longer to respond
- The latency target (300ms) was breached for the length of the test
- No requests failed — this was about speed, not errors

## Timeline

| Time | Event |
|---|---|
| T+0:00 | Delay added to checkout and deployed |
| T+0:00 | Sent test traffic to checkout |
| T+0:30 | Dashboard showed latency climbing past 300ms |
| T+2:00 | Latency alert switched from "pending" to "firing" |
| T+3:00 | Checked Jaeger traces to find where the delay was happening |
| T+4:00 | Checked logs in Loki using the trace ID |
| T+5:00 | Removed the delay and deployed the fix |
| T+6:00 | Latency back to normal, alert cleared |

## Detection

The dashboard showed latency rising clearly above the 300ms line. After the
condition held steady for 2 minutes, the alert moved from "pending" to
"firing" confirming this was a real, sustained slowdown.

**Note:** Early on, the dashboard showed a higher latency number than the
slowest individual request I could find in Jaeger. I looked into this and
found the issue was with how Prometheus groups response times into ranges
(called buckets) before calculating the 95th percentile. The default ranges
were too wide for the kind of delay I was testing, which threw off the
estimate. I fixed this by setting narrower, more specific ranges, and the
numbers lined up correctly afterward. Details and the fix are in the
Prevention section below.

## Diagnosis

Looking at the slowest traces in Jaeger, I could see the delay was happening
inside checkout itself — not in catalogue or notifications, which both
responded quickly. This made it clear right away that the problem was in
checkout's own code, not something downstream.

Checking the logs for that same request in Loki confirmed checkout received
and processed the request normally, with no errors, consistent with this
being a deliberate delay rather than something breaking.

## Root Cause

A delay was deliberately added to the checkout code to confirm that the
monitoring and alerting setup would correctly detect and report a real
slowdown.

## Resolution

Removed the delay and redeployed through the CI/CD pipeline. Latency
returned to normal within one deployment, and the alert cleared on its own
once the condition was gone.

## Prevention / Follow-up

- Being able to see exactly where the delay was happening (in checkout, not
  catalogue or notifications) made this fast to diagnose, confirms tracing
  is genuinely useful for any real slowdown in the future, not just this
  test.
- Found and fixed a separate issue along the way: the dashboard's latency
  number didn't match Jaeger's actual recorded times. This came down to
  Prometheus's default response-time ranges being too wide for the delay I
  was testing, which threw off the calculation. I set more precise ranges
  matching the values I actually care about, and the numbers now match much
  more closely.
- Alert notifications (e.g. sending to email or Teams) aren't set up yet, 
  for now I checked alerts manually in the dashboard. This is a planned next
  step.
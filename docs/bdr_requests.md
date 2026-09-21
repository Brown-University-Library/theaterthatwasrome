# BDR requests and temporary outages

TTWR uses `httpx2` for server-side BDR reads and annotation writes. The shared client applies explicit timeouts and does not retry requests automatically.

Set these optional values in the `.env` file already loaded by the application:

```dotenv
ROME_BDR_CONNECT_TIMEOUT=5
ROME_BDR_READ_TIMEOUT=10
```

Values are positive seconds, including fractional values. If omitted, they default to 5 and 10. Restart the application after changing them. Empty, nonnumeric, nonpositive, or infinite values cause a configuration error.

The connect setting also limits waiting for a connection from the client pool. The read setting limits inactivity while reading each response chunk and while writing each request chunk. These are not total page deadlines. Browser search uses their sum as a timeout for each JSONP request, because the browser does not expose separate connect and read controls here.

Timeouts, network failures, interrupted HTTP responses, and BDR HTTP 500/502/503/504 responses produce a temporary-unavailability notice. Other HTTP failures and unexpected parsing or application errors remain errors; an actual missing item still produces a 404.

Essays, shops, and biographies retain their local content when related BDR content cannot be loaded. An essay list stops making BDR requests after its first outage failure. Pages requiring BDR data return 503 with `Retry-After: 60` and prevent caching of the outage response. Search shows the same notice and cancels its outstanding requests after a failure.

The administrator-email handler excludes only 503 responses explicitly produced by the BDR outage handler. The application still logs a short reason for BDR failures. Unexpected application errors retain their existing email behavior. The separate site-checker remains responsible for outage and recovery notifications; the visitor notice describes that monitoring without claiming an alert has already been delivered.

Annotation writes are never automatically retried or redirected. If the response to a write is lost, the application cannot know whether the repository saved it. The outage page asks the editor to check the record before submitting again.

The isolated unit suite simulates BDR responses using `httpx2.MockTransport`. Run it with `uv run ./run_tests.py`; it does not require a running BDR service.

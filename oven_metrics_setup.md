# Oven metrics over the SIM7600

Connect the SIM7600 to the HMI as an IP network interface and bring up its
cellular data session with the carrier APN. On Linux, find the interface name
with `ip -br address`. On Windows, the uploader finds the IPv4 address of
the active SIMCom adapter on each retry pass. The HMI uses `curl` to bind
HTTPS uploads to that interface on Linux or to that source address on Windows.

Set these values near the top of [`oven_metrics.py`](oven_metrics.py),
then launch or restart the HMI normally.

| Python setting | Value |
| --- | --- |
| `OVEN_SERIAL` | The serial number registered with the metrics service |
| `OVEN_API_KEY` | The key provisioned for that oven |
| `WINDOWS_CELLULAR_IPV4` | Leave blank for automatic Windows detection. Set a specific IPv4 address only when needed to distinguish multiple adapters. |
| `LINUX_CELLULAR_INTERFACE` | The SIM7600's Linux interface name, such as `wwan0` or `usb0` |

Keep any copy containing a real oven key local and out of version control.
Cloud uploads are disabled until the oven identity is configured.

The HMI captures job settings at startup and queues one record when the run
ends, including early stops. Automatic runs include the program filename
and the starting steps for each active zone. Manual cooks and reheat include
starting duration and power. Queued records survive a restart and retry with
their original UUID. The queue lives under
`${XDG_STATE_HOME:-$HOME/.local/state}/altatherm/oven-metrics/`.

## Backend deployment

From the VPS, apply [the migration](server/001_oven_job_cycle_uuid.sql) to
`db_altatherm` once before deploying the updated backend.

```sh
sudo mysql db_altatherm < 001_oven_job_cycle_uuid.sql
```

Replace `oven_api.py` in the backend image's build source with
[the updated module](server/oven_api.py). Rebuild and redeploy the backend
image serving `metrics-altathermdhi.cloud` through the existing deployment
process. Its database user needs SELECT and INSERT on both `oven_jobs` and
`cooking_cycles`. Check that `/openapi.json` lists `POST /api/oven-jobs`
before testing an oven.

### Read-only React dashboard

Build the dashboard from the repository root. The build uses
`/oven-dashboard/` as its public path.

```powershell
Set-Location dashboard
npm.cmd ci
npm.cmd run build
```

Upload the contents of `dashboard/dist/` to the VPS and install them under
`/var/www/altatherm-oven-dashboard/`. Add this location to the existing
HTTPS server block for `metrics-altathermdhi.cloud`, then check and reload
Nginx with `sudo nginx -t` and `sudo systemctl reload nginx`.

```nginx
location = /oven-dashboard { return 301 /oven-dashboard/; }
location /oven-dashboard/ {
    alias /var/www/altatherm-oven-dashboard/;
    index index.html;
}
```

The app uses the same origin's `GET /api/oven-dashboard/jobs` endpoint.
Deploy the updated [backend module](server/oven_api.py) in the Docker image
for the live Compose `backend` service. For the current image-only
deployment, derive a new tag from `altatherm-backend:v2-oven-jobs` with
`COPY oven_api.py /app/oven_api.py`, then update the Compose service's
image tag. Set `OVEN_DASHBOARD_USER` and a strong, unique
`OVEN_DASHBOARD_PASSWORD` in the VPS `backend.env` file used by that
service. Use ASCII for both values and omit colons from the username.
Recreate the service with `sudo docker compose up -d --no-deps --pull never backend`.
The MySQL account must be able to select from `ovens` and `oven_jobs`.

Open `https://metrics-altathermdhi.cloud/oven-dashboard/`, sign in with
the dashboard credentials and check that the latest run appears.
The table shows times in the browser's local timezone.

## Backend contract

`POST /api/oven-jobs` accepts the job snapshots. The existing
`/api/cooking-cycles` endpoint continues to serve older queue entries
that predate the job snapshot.

Authenticate with the existing `X-Oven-Serial` and `X-Oven-Key` headers
and resolve `oven_id` from that identity. A job request looks like this.

```json
{
  "cycle_uuid": "3f48f7f0-3f08-4e1b-b8a8-f04285a4146e",
  "recipe_name": "Program 31",
  "start_time": "2026-11-19T15:00:00+00:00",
  "end_time": "2026-11-19T15:00:10+00:00",
  "result": "completed",
  "mode": "AUTO",
  "job_file": "program31.alt",
  "job_settings": {
    "zones": {
      "Zone1": [{"duration_seconds": 10.0, "power_percent": 80}]
    }
  }
}
```

For a manual or reheat run, `mode` is `MANUAL`, `job_file` is null and
`job_settings` contains `duration_seconds` and `power_percent`.
`result` is `completed`, `canceled`, or `failed`.

The endpoint stores the snapshot in `oven_jobs` and preserves the outcome
history in `cooking_cycles` in one transaction. It normalizes timestamps to
UTC and maps `end_time` to `stop_time`. A unique key on
`(oven_id, cycle_uuid)` prevents duplicate job rows and supports existing
rows with no UUID. A committed new job returns HTTP 201, an identical replay
returns HTTP 200, and changed data for the same UUID returns HTTP 409.

Verify with a registered test oven. Run an automatic program and an early
manual stop, inspect the stored settings and timestamps, then replay one
request and confirm that it still has exactly one job row.

```sql
SELECT j.job_id, j.cycle_uuid, j.mode, j.job_file, j.job_settings,
       j.start_time, j.stop_time, c.result
FROM oven_jobs AS j
JOIN cooking_cycles AS c
  ON c.oven_id = j.oven_id AND c.client_cycle_uuid = j.cycle_uuid
ORDER BY j.job_id DESC
LIMIT 10;
```

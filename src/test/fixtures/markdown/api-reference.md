# HTTP API Reference

All endpoints live under `/api` and speak JSON.

## POST /api/jobs

Creates a translation job from one or more files.

| Parameter      | Type         | Required | Description            |
| -------------- | ------------ | -------- | ---------------------- |
| `paths`        | string array | yes      | Input files or folders |
| `target_langs` | string array | yes      | e.g. `["zh-CN", "ja"]` |
| `output_dir`   | string       | no       | Defaults to `output/`  |

## GET /api/jobs/{id}

Returns the job status. Possible values:

1. `queued` — accepted, not started
2. `running` — bundles in flight
3. `completed` / `failed` / `cancelled`

## Errors

Non-existing jobs return [404](#404); invalid payloads return `400` with a
`detail` message.

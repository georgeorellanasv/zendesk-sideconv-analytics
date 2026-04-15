# Zendesk API Learnings

_Documented as we encounter quirks, undocumented behaviors, or gotchas._

## General

- Auth uses HTTP Basic with format `{email}/token` as username and the API token as password.
- All timestamps are ISO 8601 in UTC.
- Side conversation IDs are UUIDs (strings), not integers like ticket IDs.

## Rate Limits

- Standard limit: ~700 requests/minute.
- Client configured conservatively at 400 req/min.
- 429 responses include a `Retry-After` header in seconds.

## Pagination

- Most endpoints support `page` + `per_page` (offset-based).
- `GET /api/v2/views/{id}/tickets.json` supports cursor pagination via `next_page`.
- For search at scale, prefer `/api/v2/search/export.json` over `/api/v2/search.json`.

## Side Conversations

_To be filled during Phase 2 after inspecting real responses._

## Custom Fields

_To be filled after Phase 0 discovery._

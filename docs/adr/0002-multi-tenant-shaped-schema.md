# ADR 0002 — Multi-tenant-shaped, single-tenant-enforced schema

- Status: Accepted
- Date: 2026-09-06
- Phase: 1

## Context

The product is single-tenant today but must become multi-tenant later without
a data migration. Retrofitting tenancy onto a schema that never had it is
expensive and error-prone.

## Decision

Every table carries `org_id` (and `owner_id` where an owner exists) from the
first migration. Vector-store operations are scoped by a `namespace` argument
(org/collection) on every call. Enforcement today is single-org: `org_id`
defaults to a single seeded org (`Settings.DEFAULT_ORG_ID`). JWTs and API keys
already carry `org_id`.

## Consequences

- Turning on isolation later is a policy change (filter by `org_id`,
  per-org namespaces), not a migration.
- The `documents` table enforces `UNIQUE(org_id, checksum)` so checksum dedup
  is correct per-org from the start.
- Ports that touch storage (`VectorStore`, `ObjectStorage`) take a namespace
  so the tenancy hook exists before any real adapter is written.

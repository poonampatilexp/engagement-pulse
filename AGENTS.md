# Engagement Pulse — AI Engineering Instructions

## Project objective

Build a secure, multi-tenant engagement risk management application.

Consultants manage projects and risks for assigned client organisations. Client viewers can only read projects belonging to their own organisation. Authorised dashboards receive live updates without page refreshes.

## Approved technology stack

- Backend: Python 3.12, Django, Django REST Framework
- Database: PostgreSQL, Django ORM and migrations
- Authentication: JWT using Simple JWT
- Background processing: Dramatiq with Redis
- Real-time updates: Django Channels with channels_redis
- Frontend: React, Next.js App Router, TypeScript
- Server state: React Query (`@tanstack/react-query`)
- Testing: pytest, React Testing Library, Playwright
- Infrastructure: Docker Compose
- CI: GitHub Actions

Do not substitute frameworks or introduce unnecessary dependencies without approval.

## Architecture and data modelling

- Organisations own projects; projects own risks.
- Client viewers belong to one organisation.
- Consultants can access multiple organisations through a ConsultantOrganisationAccess mapping table.
- Enforce unique consultant/organisation assignments at the database level.
- Enforce organisation access on every API request and WebSocket connection.
- Never rely on frontend filtering for security.
- Use a custom Django user model from the first migration.
- Keep business logic in services rather than oversized views or serializers.
- Use database transactions for multi-step updates.

## Multi-tenant authorization

- Client viewers belong to one organisation and have read-only access.
- Consultants access multiple organisations through `ConsultantOrganisationAccess`.
- Enforce unique consultant/organisation assignments in PostgreSQL.
- Scope list and detail queries to authorised organisations.
- Apply organisation checks to nested resources, CSV jobs and WebSocket connections.
- Return 403 for unauthorised operations and 404 for inaccessible tenant resources.
- Enforce permissions in the backend ORM, services and API layer.

## Risk scoring

- Severity values: low, medium, high, critical.
- Status values: open, mitigating, closed.
- Keep allowed severity/status choices in application code.
- Calculate individual risk scores as `SeverityWeight × StatusWeight`.
- Calculate project risk scores as `min(100, sum(individual risk scores))`.
- Default severity weights: low=1, medium=2, high=3, critical=4.
- Default status weights: open=3, mitigating=2, closed=0.
- Store severity weights and status weights in PostgreSQL.
- Cache the calculated score on each project.
- Recalculate after risk changes, scoring configuration changes and successful CSV imports.
- Use concurrency-safe database transactions and locking where needed.

## CSV Background Processing

- Accept CSV uploads and immediately return a job ID.
- Calculate a SHA-256 fingerprint of uploaded file contents.
- Deduplicate imports using project, submitting user and file fingerprint.
- Enforce database uniqueness to prevent concurrent duplicate jobs.
- Return the existing job ID for duplicate submissions.
- Process CSV imports asynchronously using Dramatiq and Redis.
- Validate CSV structure, required fields and field values.
- Import records within a database transaction.
- Recalculate the project risk score after successful import.
- Track job status (queued, processing, completed, failed) in PostgreSQL.
- Handle worker retries and duplicate task deliveries safely.
- Expose an API endpoint to retrieve job status and errors.
- Broadcast successful import updates through Django Channels and Redis.
- Use shared file storage accessible to API and worker containers.

## Real-time architecture

- Use Django ASGI, Channels and Redis channel layers.
- Broadcast changes only after successful database commit.
- Authorise WebSocket connections by project and organisation.
- Do not place long-lived JWTs in WebSocket URLs.
- Use short-lived connection tickets or another explicitly reviewed secure approach.
- Include event IDs and project IDs in update messages.
- React Query should invalidate/refetch affected queries after events.
- Reconnect safely and refetch after reconnect.
- Test broadcasting with multiple API instances.
- Document that a transactional outbox would improve delivery guarantees in production.

## Frontend requirements

- Login page, project list and project dashboard.
- Consultants can create/update permitted records.
- Client viewers have read-only access.
- Include loading, empty, error and permission-denied states.
- Provide labelled forms, keyboard support and accessible contrast.
- Use React Query for server state, not Redux.
- Keep API contracts typed.

## Testing and quality

- Add backend tests for authentication, tenant isolation, scoring and CSV idempotency.
- Include a test proving one client viewer cannot access another organisation's data.
- Include at least one React Testing Library test.
- Include at least one Playwright end-to-end workflow.
- Run relevant tests after each milestone.
- Never claim tests pass without executing them.
- Do not hide errors, fabricate outputs or silently skip requirements.

## Git workflow

- Work only on the develop branch.
- master contains verified, finalised milestones.
- Never push or merge into master automatically.
- Do not rewrite history or force-push.
- Propose small, meaningful commits after verified milestones; commit only with explicit approval.
- Explain what was changed and tested before committing.
- Never commit secrets, credentials, .env files or generated caches.
- Update README alongside implementation changes.

## Documentation

- Maintain local setup instructions and seeded demo logins.
- Record three architecture decision records.
- Include an Azure deployment and Entra ID migration note of no more than one page.
- Include a README section describing the equivalent FastAPI implementation.
- Disclose AI-assisted development accurately.
- Document incomplete functionality and trade-offs.

## Operating instructions for the coding agent

Before each task:

1. Read this AGENTS.md completely.
2. Confirm the current Git branch is develop.
3. Inspect existing code before making changes.
4. State assumptions and identify missing dependencies.
5. Implement only the requested milestone.
6. Run relevant verification commands when possible.
7. Report files changed, tests executed, results and limitations.
8. Update README when behaviour or setup changes.
9. Do not merge to master without explicit user approval.

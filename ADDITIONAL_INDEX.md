# Additional Database Indexes

## Submission Timestamp Index

The `submissions` table is missing an index on the `timestamp` column, which is used for `ORDER BY timestamp DESC` with pagination on the submissions listing page (`/contest/<id>/submissions`).

### Recommended Index

A composite index on `(task_id, timestamp DESC)` covers both the JOIN filter and the sort order, allowing PostgreSQL to avoid a separate sort step:

```sql
CREATE INDEX ix_submissions_task_id_timestamp ON submissions (task_id, timestamp DESC);
```

This replaces the existing single-column `task_id` index (`ix_submissions_task_id`), which becomes redundant since the composite index serves the same purpose as a leftmost prefix.

To drop the redundant index:

```sql
DROP INDEX IF EXISTS ix_submissions_task_id;
```

### Why

The submissions page query joins `submissions` to `tasks`, filters by `tasks.contest_id`, and orders by `submissions.timestamp DESC` with `LIMIT/OFFSET` for pagination. Without an index on `timestamp`, PostgreSQL must fetch all matching rows and perform a filesort on every request. As submission count grows, this gets progressively slower.

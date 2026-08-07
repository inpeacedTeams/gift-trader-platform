# Database migrations

The repository uses ordered SQL migrations in `versions/`.

Run them with:

```bash
python -m app.db.migrate
```

The runner creates `schema_migrations`, applies files in lexical order, and records each filename transactionally. Existing migrations use `CREATE TABLE IF NOT EXISTS` so a previously initialized database can be reconciled safely.

There are two legacy `0002` filenames because the early project snapshots used separate feature tracks. The runner identifies migrations by filename and applies both in lexical order. New migrations must use the next unique filename, never reuse an existing prefix.

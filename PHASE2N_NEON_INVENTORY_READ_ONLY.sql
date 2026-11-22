-- Phase 2N. Run in Neon SQL Editor. READ ONLY. No user data or credentials returned.
-- 1. All non-system schemas, tables and views (including unexpected additions)
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
-- 2. All columns in non-system schemas, for manual personal-data review
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name, ordinal_position;
-- 3. Foreign keys and possible dependent records
SELECT tc.table_schema, tc.table_name, kcu.column_name,
       ccu.table_schema AS referenced_schema, ccu.table_name AS referenced_table,
       ccu.column_name AS referenced_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name=ccu.constraint_name AND tc.table_schema=ccu.table_schema
WHERE tc.constraint_type='FOREIGN KEY'
ORDER BY tc.table_schema, tc.table_name;
-- This does NOT inspect logs, backups, object stores, exports or eBay notification payloads.

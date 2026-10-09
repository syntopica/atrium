"""The index schema. Every table here is derived and safe to drop."""

from atrium.sql.load_sql import load_sql

# The statements, and the reasons behind each table, live in the resource file.
SCHEMA = load_sql("store/schema")

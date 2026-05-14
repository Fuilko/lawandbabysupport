"""LegalShield crawlers package.

Each module collects one source of Japanese public statistics / legal data,
normalizes it, and writes Parquet files into ../knowledge/parsed/.
A separate ingest step loads them into ../knowledge/unified.duckdb.
"""

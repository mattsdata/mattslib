# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-11-03

### Added
- `retry` / `async_retry`: exponential backoff with full jitter.
- `setup_logging` / `JsonFormatter`: one-call structured JSON logging.
- `load_config`: typed settings from environment variables, reporting all errors at once.
- `ttl_cache`: thread-safe in-memory cache with expiry and LRU eviction.
- `Timer` / `timed`: duration measurement.
- `atomic_write`, `file_hash`, `chunked`: safe file and batching helpers.

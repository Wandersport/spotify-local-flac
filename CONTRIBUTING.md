# Contributing to Spotify Local FLAC

Thank you for your interest in improving Spotify Local FLAC!

## Development Guidelines

1. **Architecture & Scope**:
   - The project strictly respects legal and security boundaries.
   - We **never** decrypt, intercept, or modify Spotify DRM-protected streams.
   - The project is designed exclusively for user-owned local audio files.

2. **Code Structure**:
   - `server/`: Lightweight Python 3 companion daemon. Zero external binary dependencies beyond `mutagen` and Python standard library.
   - `spicetify/`: Custom App React interface and global playback extension.
   - `tests/`: Automated unit and integration test suite.
   - `systemd/`: User service configuration.

3. **Running Tests**:
   Before submitting changes, ensure all tests pass:
   ```bash
   # Run full unit and integration test suite
   python3 -m unittest discover tests

   # Run performance benchmarks
   python3 tests/benchmark.py

   # Run frontend table sorting tests
   node tests/test_table_sorting.js
   ```

4. **Code Quality**:
   - Keep memory usage low; do not read entire audio files into RAM.
   - Maintain HTTP Range (206 Partial Content) compliance.
   - Ensure all filesystem paths are sanitized to prevent directory traversal.

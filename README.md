# Oasis

Oasis is a modern, web-based Media Dashboard and Streaming application built entirely in Python. Designed as a complete ground-up rewrite (V2), Oasis refines core architectural patterns following a thorough retrospective of the initial implementation.

It leverages **NiceGUI** for its responsive frontend and media streaming interface—integrating smoothly over private networks like **Tailscale**—and uses **SQLAlchemy** powered by an optimized **SQLite-WAL** database backend.

> **Note:** Currently, Oasis supports local management and streaming for **Video**, **Image**, and **Comic** media types. Audio and Book extensions, along with online scraping/bookmarking, are planned for future releases.

---

## Key Features & Architecture

* **Modular UI Components:** Powered by NiceGUI with custom transparent page stacking (`web_stack.py`) to support rich, overlay-based views while preserving full browser history navigation and deep-linking URL support.
* **Smart Navigation Engine:** Recreates exact query parameters from previous view states to enable seamless "Next / Previous" media cycling across paginated views.
* **Optimized Background Processing:**
  * **Metadata Extraction:** Multi-threaded asynchronous workers handling I/O-bound metadata parsing.
  * **Thumbnail Generation:** Multi-processed workers preventing CPU bottlenecks during heavy video/image rendering tasks.
* **High-Performance SQLite-WAL Database:** Configured with Write-Ahead Logging for high-concurrency read operations during streaming and background indexing.
* **Tailscale Compatibility:** Built-in network configuration options for seamless remote access over private mesh VPNs.

---

## File Structure & Module Overview

```text
├── main.py                 # Application entry point, routing, and DB initialization
├── database.py             # SQLAlchemy models, SQLite-WAL configuration, and schema
├── scanner.py              # Recursive file system scanner and task queue producer
├── metadata_worker.py      # Async multi-threaded worker for media metadata extraction
├── thumb_worker.py         # Multi-processed worker for video/image thumbnail creation
├── navigation_engine.py    # Cross-page query recreation for next/prev media navigation
├── web_stack.py            # Transparent page-stacking architecture
├── cards.py                # Reusable media card UI components
├── header.py               # Persisted background color and scrolling navigation header
├── home.py                 # Home page view displaying media rows
├── local.py                # Paginated media library with filtering and custom views
├── local_view.py           # Transparent overlay modal for detailed single-item viewing
├── settings.py             # Directory management, worker toggles, and manual scanning
├── bookmark.py             # [Planned] Bookmark management view
└── scraper.py              # [Planned] External media scraping engine
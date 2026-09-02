# Oasis

Oasis is a web-based Media Dashboard and Streaming application built entirely in Python. Designed as a complete rewrite, Oasis refines core architectural patterns following a retrospective of the initial implementation.

It leverages **NiceGUI** for its frontend and media streaming interface, integrating over private networks like **Tailscale**, and uses **SQLAlchemy** powered by **SQLite-WAL** database backend.

> **Note:** Currently, Oasis only supports local management and streaming for **Video**, **Image**, and **Comic** media types. Audio and Book extensions, along with online scraping/bookmarking, are planned for future releases.

---

## Key Features & Architecture

* **Modular UI Components:** Powered by NiceGUI with custom transparent page stacking (`web_stack.py`) to support transparent single item views while preserving full browser history navigation and URL support.
* **Navigation Engine:** Recreates exact query parameters from previous view states to enable seamless "Next / Previous" media cycling across paginated views.
* **Optimized Background Processing:**
  * **Metadata Extraction:** Multi-threaded asynchronous workers handling I/O-bound metadata parsing.
  * **Thumbnail Generation:** Multi-processed workers preventing CPU bottlenecks during heavy video/image rendering tasks.
* **High-Performance SQLite-WAL Database:** Configured with Write-Ahead Logging for high-concurrency read operations during streaming and background indexing.
* **Tailscale Compatibility:** Built-in network configuration for seamless remote access over private mesh VPNs. Currently Adjusted manually in main.py with DOMAIN_NAME and ui.run params.

---

## File Structure & Module Overview

```text
├── main.py                 # Application entry point, routing, and DB initialization
├── Pages/
│   ├── bookmark.py         # [Planned] Bookmark management view
│   ├── home.py             # Home page view displaying media rows
│   ├── local.py            # Paginated media library with filtering and custom views
│   ├── local_view.py       # Transparent overlay modal for detailed single-item viewing
│   ├── scraper.py          # [Planned] External media scraping engine
│   └── settings.py         # Directory management, worker toggles, and manual scanning
└── Tools/
    ├── cards.py            # Reusable media card UI components
    ├── database.py         # SQLAlchemy models, SQLite-WAL configuration, and schema
    ├── header.py           # Persisted background color and scrolling navigation header
    ├── metadata_worker.py  # Async multi-threaded worker for media metadata extraction
    ├── navigation_engine.py       # Cross-page query recreation for next/prev media navigation
    ├── scanner.py          # Recursive file scanner and task queue producer
    ├── thumb_worker.py     # Multi-processed worker for video/image/comic thumbnail creation
    └── web_stack.py        # Transparent page-stacking tool

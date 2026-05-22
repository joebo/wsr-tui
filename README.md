# wsr_tui
Proof of Concept Wall Street Raider Text User Interface (TUI)

<img width="1080" height="608" alt="wsr-tui demo" src="https://github.com/user-attachments/assets/a445bd6c-aea2-4d35-b816-aab6df48fa2f" />

# WSR TUI

Textual-based terminal UI for interacting with Wall Street Raider through its local REST API.

## Tech stack

- Python
- [Textual](https://textual.textualize.io/) for the TUI
- `httpx` for direct HTTP access on Windows
- WSL-to-Windows stdio bridge for WSL usage

## Architecture

Wall Street Raider exposes a local REST API on `127.0.0.1` using an ephemeral port written to:

`%LOCALAPPDATA%\Wall Street Raider\runtime.json`

This app supports two modes:

- **Windows:** reads `runtime.json` and talks to the REST API directly with HTTP
- **WSL:** launches `wsr_rest_helper.py` as a Windows subprocess and sends JSON-line requests over stdin/stdout; the helper reads `runtime.json` and forwards requests to the Windows-local REST API

## Notes

- Ports change every launch, so `runtime.json` is the source of truth
- The WSL bridge avoids exposing extra network ports or changing firewall rules
  

[Youtube demo](https://youtu.be/CDQY0legCuY)

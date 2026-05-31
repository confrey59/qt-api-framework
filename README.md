# qt-api-framework
**Modular, API-driven desktop GUI framework built on PySide6.**

Zero domain logic in the core. Pure client that speaks REST+WebSocket.  
Cross-platform (Linux/macOS/Windows), thread-safe, pip-installable.

## Architecture
- **MainShell**: QMainWindow + QMdiArea, status bar, theme, auth gate
- **QtNetworkWorker**: QThread wrapper for httpx + websockets (sync, thread-safe)
- **PluginLoader**: dynamic JSON-driven plugin loading with lifecycle hooks
- **AuthFlow**: login/session state machine with Bearer token injection

## Installation
 ```bash
git clone https://github.com/confrey59/qt-api-framework.git
cd qt-api-framework
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick Start
```bash
# Launch with example plugins
qt-api-framework --config config/framework.json --plugins examples/plugins.json

# Or run as module
python -m qt_api_framework --plugins examples/plugins.json
```

## Configuration
| File | Purpose |
|------|---------|
| `framework.json` | `api_base_url`, `ws_base_url`, `theme`, `auth_enabled`, `timeout` |
| `plugins.json` | Plugin registry: `id`, `module`, `class`, `requires_auth` |

## Plugin Development
Plugins live in separate directories or pip packages. The repo includes `examples/reference_plugin/` as the official template.

### 1. Minimal Structure
```text
examples/
└ my_plugin/
├├ __init__.py
    ├┑ plugin.py
```

### 2. BasePlugin Contract
Inherit from `BasePlugin` and implement 3 methods:
- `create_window() -> QWidget`: The plugin UI
- `on_load() -> None`: Setup WS, threads, initial data fetch
- `on_unload() -> None`: Cleanup threads, sockets, disconnect signals

### 3. Thread-Safe Network Calls
Never use `httpx` directly in plugins. Use the injected client:
```python
self.api_client.request_post.emit("/endpoint", {"json": {"key": "value"}})
self.api_client.request_finished.connect(self._handle_response)
```
Calls execute in a dedicated QThread. Zero GUI blocking.

### 4. Registration
Add your plugin to `plugins.json`:
```json
"{
    "plugins": [
        {
            "id": "my_plugin",
            "module": "examples.my_plugin.plugin",
            "class": "MyPlugin",
            "title": "My Plugin",
            "requires_auth": true
        }
    ]
}
```

## Testing
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tests/test_step1.py
QTQPAPATFORM=offscreen PYTHONPATH=src python tests/test_step2.py
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tests/test_step0.py
```

## License
MIT © 2024-2026

import os
import sys
from urllib.parse import quote

import requests
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QCompleter,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Configure Chromium flags before creating any web views.
_existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
_required_flags = (
    "--disable-features=WebGPU --disable-logging --log-level=3"
)
for _flag in _required_flags.split():
    if _flag not in _existing_flags:
        _existing_flags = f"{_existing_flags} {_flag}".strip()
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = _existing_flags


BULBAPEDIA = "https://bulbapedia.bulbagarden.net/wiki/"
SMOGON = "https://www.smogon.com/dex/sv/pokemon/"
POKEMON_TAG = "_(Pok%C3%A9mon)"


def normalize_smogon_name(raw_name: str) -> str:
    normalized = raw_name.strip().lower().replace(" ", "-")
    return quote(normalized, safe="-")


def normalize_bulbapedia_name(raw_name: str) -> str:
    pieces = [
        piece.capitalize()
        for piece in raw_name.strip().replace("-", " ").split()
    ]
    normalized = "_".join(pieces)
    return quote(normalized, safe="_")


def fetch_all_pokemon_names() -> list[str]:
    try:
        response = requests.get(
            "https://pokeapi.co/api/v2/pokemon?limit=2000",
            timeout=12,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        return [item["name"] for item in data.get("results", [])]
    except requests.RequestException:
        return []


class PokemonCompleter(QCompleter):
    def splitPath(self, path: str) -> list[str]:
        # Treat spaces like hyphens so "iron " matches "iron-..."
        normalized = path.lower().replace(" ", "-")
        return [normalized]


class QuietWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        # Suppress site console output in normal use. Set POKEBROWSER_DEBUG_JS=1
        # to forward JavaScript console messages for troubleshooting.
        if os.environ.get("POKEBROWSER_DEBUG_JS", "") != "1":
            return
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class TrackerBlocker(QWebEngineUrlRequestInterceptor):
    BLOCKED_DOMAINS = {
        "pmbmonetize.live",
        "nextmillmedia.com",
        "ingage.tech",
        "doubleclick.net",
        "googlesyndication.com",
        "googletagmanager.com",
        "google-analytics.com",
        "adnxs.com",
        "pubmatic.com",
        "criteo.com",
        "taboola.com",
        "outbrain.com",
        "celtra.com",
        "quantserve.com"
    }

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        host = info.requestUrl().host().lower()
        if not host:
            return
        if any(
            host == blocked or host.endswith(f".{blocked}")
            for blocked in self.BLOCKED_DOMAINS
        ):
            info.block(True)


class PokemonBrowser(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PokeDex Browser")
        self.resize(1200, 800)
        self.tracker_blocker = TrackerBlocker()
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(
            self.tracker_blocker
        )

        # Search controls
        self.input_label = QLabel("Pokemon:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g., charizard")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.handle_search)
        self.search_input.returnPressed.connect(self.handle_search)
        self.setup_autocomplete()

        search_row = QHBoxLayout()
        search_row.addWidget(self.input_label)
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_button)

        # Tabs with two browsers
        self.tabs = QTabWidget()
        self.bulbapedia_view = QWebEngineView()
        self.smogon_view = QWebEngineView()
        self.bulbapedia_view.setPage(QuietWebEnginePage(self.bulbapedia_view))
        self.smogon_view.setPage(QuietWebEnginePage(self.smogon_view))

        self.tabs.addTab(self.bulbapedia_view, "Bulbapedia")
        self.tabs.addTab(self.smogon_view, "Smogon")
        self.setup_shortcuts()

        # Status text
        self.status_label = QLabel("Ready.")

        root_layout = QVBoxLayout()
        root_layout.addLayout(search_row)
        root_layout.addWidget(self.tabs)
        root_layout.addWidget(self.status_label)
        self.setLayout(root_layout)

        # Load home pages initially
        self.load_home_pages()
        if not self.pokemon_names:
            self.status_label.setText(
                "Loaded home pages. Autocomplete unavailable (network issue)."
            )

    def load_home_pages(self) -> None:
        self.bulbapedia_view.setUrl(QUrl(BULBAPEDIA))
        self.smogon_view.setUrl(QUrl(SMOGON))
        self.status_label.setText("Loaded home pages.")

    def setup_autocomplete(self) -> None:
        self.pokemon_names = fetch_all_pokemon_names()
        if not self.pokemon_names:
            return

        completer = PokemonCompleter(self.pokemon_names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.search_input.setCompleter(completer)

    def setup_shortcuts(self) -> None:


        self.bulbapedia_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        self.bulbapedia_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.bulbapedia_shortcut.activated.connect(self.go_to_bulbapedia_tab)


        self.bulbapedia_shortcut_mac = QShortcut(QKeySequence("Meta+1"), self)
        self.bulbapedia_shortcut_mac.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.bulbapedia_shortcut_mac.activated.connect(self.go_to_bulbapedia_tab)


    def go_to_bulbapedia_tab(self) -> None:
        if self.tabs.currentIndex() == 0:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)

    def handle_search(self) -> None:
        raw = self.search_input.text()
        if not raw.strip():
            self.status_label.setText("Please enter a Pokemon name.")
            return

        smogon_name = normalize_smogon_name(raw)
        bulbapedia_name = normalize_bulbapedia_name(raw)
        self.bulbapedia_view.setUrl(
            QUrl(f"{BULBAPEDIA}{bulbapedia_name}{POKEMON_TAG}")
        )
        self.smogon_view.setUrl(
            QUrl(f"{SMOGON}{smogon_name}")
        )
        self.status_label.setText(
            f"Loaded Bulbapedia and Smogon for '{raw.strip()}'."
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = PokemonBrowser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


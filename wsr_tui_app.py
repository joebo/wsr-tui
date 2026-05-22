#"startingMoney=500|gameLength=35|difficultyLevel=2|startPaused=0|player2Name=Big Money|player1Name=Wally Raider|player3Name=Oddlot Roger|player4Name=Gordon Gekko|player5Name=Tony Stark"
import argparse
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Vertical, Container
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Static, OptionList, Tree, DataTable, Button
from textual.widgets.option_list import Option
from textual.widgets.tree import TreeNode
from textual.message import Message

parser = argparse.ArgumentParser(description="Launch or inspect Wall Street Raider runtime metadata.")
parser.add_argument(
    "--existing",
    action="store_true",
    help="Do not kill or launch wsr.exe; read existing runtime.json instead.",
)
args = parser.parse_args()

os.environ["ENVIRONMENT"] = "09a7sd0(&)(Fd70s(*S&DF)987df0ds987f09&)F97)F&(*D7f9s7d0(S*D&f09d8s7f0s97F)(7d))"

is_wsl = os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower()

if is_wsl:
    RUNTIME_JSON_PATH = None
    current_dir = str(Path(__file__).parent)
    wsl_to_windows = subprocess.run(["wslpath", "-w", current_dir], capture_output=True, text=True)
    windows_dir = wsl_to_windows.stdout.strip()
    print("WSL detected. Converted current directory to Windows path:", windows_dir)
    helper_log = open("/tmp/wsr_rest_helper.log", "a", encoding="utf-8")
    proc = subprocess.Popen(
        [
            "/mnt/c/Windows/System32/cmd.exe",
            "/c",
            "python",
            "-u",
            f"{windows_dir}\\wsr_rest_helper.py",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
else:
    RUNTIME_JSON_PATH = Path.home() / "AppData" / "Local" / "Wall Street Raider" / "runtime.json"

MODAL_TEXT_REGEX = re.compile(r'"modalText"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"')
MODAL_TYPE_REGEX = re.compile(r'"modalType"\s*:\s*(\d+)')

COMMAND_LIST = [
    "status", "gamestate", "quote", "asset_chart", "database_data", "ownership_tree",
    "subsidiaries_tree", "newgame", "loadgame", "load_specific_save", "savegame",
    "savegameas", "exit_game", "check_scoreboard", "start_ticker", "run_ticker",
    "stop_ticker", "set_ticker_speed", "ticker_advance", "clear_event_string",
    "splash_screen_played", "buy_stock", "sell_stock", "short_stock", "cover_short_stock",
    "buy_corporate_bond", "sell_corporate_bond", "buy_long_govt_bonds", "sell_long_govt_bonds",
    "buy_short_govt_bonds", "sell_short_govt_bonds", "buy_commodity_futures", "sell_commodity_futures",
    "close_long_commodity_futures_by_slot", "short_commodity_futures", "cover_short_commodity_futures",
    "cover_short_commodity_futures_by_slot", "buy_physical_commodity", "sell_physical_commodity",
    "buy_physical_crypto", "sell_physical_crypto", "buy_crypto_futures", "sell_crypto_futures",
    "buy_calls", "sell_calls", "buy_puts", "sell_puts", "advanced_options_trading",
    "exercise_call_options_early", "exercise_put_options_early", "prepay_taxes", "elect_ceo",
    "resign_as_ceo", "change_managers", "set_dividend", "set_productivity", "set_growth_rate",
    "restructure", "buy_corporate_assets", "sell_corporate_assets", "offer_corporate_assets_for_sale",
    "view_for_sale_items", "sell_subsidiary_stock", "rebrand", "toggle_company_autopilot",
    "toggle_global_autopilot", "become_etf_advisor", "set_advisory_fee", "decrease_earnings",
    "increase_earnings", "merger", "greenmail", "lbo", "startup", "capital_contribution",
    "public_stock_offering", "private_stock_offering", "issue_new_corp_bonds", "redeem_corp_bonds",
    "extraordinary_dividend", "tax_free_liquidation", "taxable_liquidation", "spin_off",
    "split_stock", "reverse_split_stock", "borrow_money", "repay_loan", "advance_funds",
    "call_in_advance", "interest_rate_swaps", "view_swap_details", "terminate_swap",
    "set_bank_allocation", "trade_tbills", "list_bank_loans", "change_bank", "call_in_loan",
    "buy_bank_loans", "buy_business_loans", "sell_business_loan", "buy_consumer_loans",
    "sell_consumer_loans", "buy_prime_mortgages", "sell_prime_mortgages", "buy_subprime_mortgages",
    "sell_subprime_mortgages", "list_etfs", "freeze_all_loans", "freeze_loan", "change_law_firm",
    "credit_info", "antitrust_lawsuit", "harrassing_lawsuit", "spread_rumors", "set_active_ui_report",
    "set_view_asset", "set_view_industry", "database_search", "clear_chart", "growth_throttle",
    "clear_stream_list", "fill_stream_list", "toggle_streaming_quote", "nav_back", "nav_forward",
    "nav_clear", "nav_goto", "nav_set_history", "set_who_owns_filter", "view_current_interest_rates",
    "whos_ahead", "db_research_tool", "economic_stats", "most_cash_report", "largest_market_cap",
    "largest_tax_losses", "industry_summary", "industry_projections", "view_corp_assets_for_sale",
    "supp_earn_select", "currency_select", "supp_warn_select", "suppress_select", "autosave_select",
    "exercise_select", "sweep_select", "makedelivery_select", "takedelivery_select", "tooltips_select",
    "shareholdergraph_select", "disablehotkeys_select", "autoadd_select", "set_chart_type",
    "set_locale", "cheat_disable", "cheat_disable_lawsuits", "cheat_merger_info", "cheat_earnings_info",
    "cheat_add_cash", "close_modal", "modal_result", "set_tutorial_step", "set_tutorial_enabled",
    "show_price_alerts", "create_price_alert", "delete_price_alert", "set_custom_data"
]

GET_ONLY_ENDPOINTS = {
    "status", "gamestate", "quote", "database_data", "ownership_tree", "subsidiaries_tree"
}

ID_ONLY_ENDPOINTS = {
    "asset_chart",
    "set_ticker_speed",
    "toggle_company_autopilot",
    "call_in_advance",
    "call_in_loan",
    "sell_business_loan",
    "freeze_loan",
    "set_active_ui_report",
    "set_view_asset",
    "set_view_industry",
    "toggle_streaming_quote",
    "nav_goto",
    "set_chart_type",
    "set_tutorial_step",
    "set_tutorial_enabled",
    "delete_price_alert",
}

INTPARAM2_ONLY_ENDPOINTS = {
    "buy_long_govt_bonds", "sell_long_govt_bonds",
    "buy_short_govt_bonds", "sell_short_govt_bonds",
    "advanced_options_trading",
    "prepay_taxes", "elect_ceo", "resign_as_ceo", "change_managers",
    "set_dividend", "set_productivity", "set_growth_rate", "restructure",
    "buy_corporate_assets", "sell_corporate_assets", "offer_corporate_assets_for_sale",
    "view_for_sale_items", "rebrand", "toggle_global_autopilot",
    "become_etf_advisor", "set_advisory_fee", "decrease_earnings", "increase_earnings",
    "startup", "capital_contribution", "public_stock_offering", "private_stock_offering",
    "issue_new_corp_bonds", "redeem_corp_bonds", "extraordinary_dividend",
    "tax_free_liquidation", "taxable_liquidation", "split_stock", "reverse_split_stock",
    "borrow_money", "repay_loan", "advance_funds", "set_bank_allocation", "trade_tbills",
    "list_bank_loans", "change_bank", "buy_business_loans", "buy_consumer_loans",
    "sell_consumer_loans", "buy_prime_mortgages", "sell_prime_mortgages",
    "buy_subprime_mortgages", "sell_subprime_mortgages", "freeze_all_loans",
    "change_law_firm", "credit_info",
}

ID_INTPARAM2_ENDPOINTS = {
    "buy_stock", "sell_stock", "short_stock", "cover_short_stock",
    "buy_corporate_bond", "sell_corporate_bond",
    "buy_commodity_futures", "sell_commodity_futures",
    "close_long_commodity_futures_by_slot",
    "short_commodity_futures", "cover_short_commodity_futures",
    "cover_short_commodity_futures_by_slot",
    "buy_physical_commodity", "sell_physical_commodity",
    "buy_physical_crypto", "buy_crypto_futures", "sell_crypto_futures",
    "exercise_call_options_early", "exercise_put_options_early",
    "sell_subsidiary_stock",
    "merger", "greenmail", "lbo", "spin_off",
    "interest_rate_swaps", "view_swap_details", "terminate_swap",
    "antitrust_lawsuit", "harrassing_lawsuit", "spread_rumors",
}

STR_ENDPOINTS = {
    "set_locale",
    "create_price_alert",
}

FILENAME_ENDPOINTS = {
    "load_specific_save",
    "savegameas",
}

VALUE_ENDPOINTS = {
    "set_who_owns_filter",
}

ANSWER_OR_STR_ENDPOINTS = {
    "modal_result",
}

UNDERLYING_ENDPOINTS = {
    "buy_calls",
    "sell_calls",
    "buy_puts",
    "sell_puts",
}


class ValuePopup(ModalScreen[None]):
    CSS = """
    ValuePopup {
        align: center middle;
    }
    #value-popup-container {
        width: 80%;
        height: 80%;
        border: round white;
        background: #111111;
        padding: 1;
    }
    #value-popup-title {
        height: 3;
        color: cyan;
        text-style: bold;
    }
    #value-popup-body {
        height: 1fr;
        border: round green;
        padding: 1;
    }
    #value-popup-buttons {
        height: 3;
        align: center middle;
        padding-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "close_popup", "Close"),
        ("enter", "close_popup", "Close"),
    ]

    def __init__(self, title: str, body: str):
        super().__init__()
        self.popup_title = title
        self.popup_body = body

    def compose(self) -> ComposeResult:
        with Container(id="value-popup-container"):
            yield Static(self.popup_title, id="value-popup-title")
            with VerticalScroll(id="value-popup-body"):
                yield Static(self.popup_body)
            with Horizontal(id="value-popup-buttons"):
                yield Button("Close", id="close-popup-button", variant="primary")

    def action_close_popup(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-popup-button":
            self.dismiss(None)


class AutocompleteInput(Input):
    class ControlKey(Message):
        def __init__(self, action: str) -> None:
            super().__init__()
            self.action = action

    def on_key(self, event) -> None:
        if event.key in ("tab", "up", "down"):
            event.stop()
            event.prevent_default()
            self.post_message(self.ControlKey(event.key))


class WSRTextualApp(App):
    CSS = """
    Screen {
        background: black;
    }
    #main {
        height: 1fr;
    }
    .scroll-box {
        width: 30%;
        height: 100%;
        border: round green;
        padding: 1;
    }
    #inspector-container {
        width: 70%;
        height: 100%;
    }
    #inspector-tree {
        width: 50%;
        height: 100%;
        border: round blue;
    }
    #watch-pane {
        width: 50%;
        height: 100%;
    }
    #pin_input {
        border: round magenta;
        height: 3;
    }
    #watch-window {
        height: 1fr;
        border: round cyan;
    }
    #controls {
        dock: bottom;
        height: auto;
    }
    #autocomplete_list {
        height: 6;
        background: #111;
        border: solid gray;
        display: none;
    }
    #command_input {
        height: 3;
        border: round yellow;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("p", "pin_node", "Pin Selected Tree Node"),
        ("u", "unpin_selected_watch", "Unpin Selected Watch"),
        ("d", "show_details_for_focused_widget", "Show Details"),
        ("r", "refresh_tree", "Refresh Tree Snapshot"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_lines: list[str] = []
        self.rest_port: int | None = None
        self.last_raw_payload: str = ""
        self.last_seen_modal_text: str = ""
        self.last_seen_modal_type: int | None = None
        self.current_matches: list[str] = []
        self.command_history: list[str] = []
        self.history_pointer: int = -1
        self.temporary_input_buffer: str = ""
        self.force_poll_flag: bool = False
        self.raw_json_data = {}
        self.bridge_lock = threading.Lock()
        self.watched_paths = [
            ["activeEntityData", "price"],
            ["activeEntityFinancials", "cash"],
            ["activeEntityFinancials", "operatingProfit"],
        ]
        self.tree_initially_populated = False
        self.path_col = None
        self.value_col = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with VerticalScroll(id="log-container", classes="scroll-box"):
                yield Static(id="log")
            with Horizontal(id="inspector-container"):
                yield Tree("Gamestate Root", id="inspector-tree")
                with Vertical(id="watch-pane"):
                    yield Input(placeholder="Path to pin (e.g. allCompanies.0.price)", id="pin_input")
                    yield DataTable(id="watch-window")
        with Vertical(id="controls"):
            yield OptionList(id="autocomplete_list")
            yield AutocompleteInput(placeholder="Type an API command...", id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        self.update_log()
        self.table = self.query_one("#watch-window", DataTable)
        self.path_col, self.value_col = self.table.add_columns("Pinned Path", "Live Value")
        self.table.cursor_type = "row"

        for path in self.watched_paths:
            path_str = ".".join(path)
            self.table.add_row(path_str, "Awaiting Stream...", key=path_str)

        if is_wsl:
            self.update_log_system("System: Connected via wsr_rest_helper")
        else:
            if self.load_runtime_port():
                self.update_log_system(f"System: Connected via local port {self.rest_port}.")

        self.run_worker(self.persistent_gamestate_loop, thread=True)
        self.query_one("#command_input", AutocompleteInput).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "pin_input":
            return
        if self.history_pointer != -1:
            return

        text = event.value.strip().lower()
        opt_list = self.query_one("#autocomplete_list", OptionList)

        if not text:
            opt_list.styles.display = "none"
            self.current_matches = []
            return

        base_command = text.split()[0]
        self.current_matches = [cmd for cmd in COMMAND_LIST if cmd.startswith(base_command)]

        if self.current_matches and base_command != self.current_matches[0]:
            opt_list.clear_options()
            for match in self.current_matches[:10]:
                opt_list.add_option(Option(match))
            opt_list.styles.display = "block"
            if opt_list.highlighted is None:
                opt_list.highlighted = 0
        else:
            opt_list.styles.display = "none"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "pin_input":
            raw_path = event.value.strip()
            if raw_path:
                path_parts = raw_path.split(".")
                self._add_watch(path_parts)
                event.input.value = ""
            self.query_one("#command_input", AutocompleteInput).focus()
            return

        raw_value = event.value.strip()
        if not raw_value:
            return

        if not self.command_history or self.command_history[-1] != raw_value:
            self.command_history.append(raw_value)

        self.history_pointer = -1
        self.temporary_input_buffer = ""
        self.query_one("#autocomplete_list", OptionList).styles.display = "none"
        event.input.value = ""
        self.append_log(f"> {raw_value}")
        await self.process_and_send_command(raw_value)

    def _handle_new_gamestate(self, payload: dict) -> None:
        self.raw_json_data = payload
        self.update_watch_window()
        if not self.tree_initially_populated:
            self.tree_initially_populated = True
            self.refresh_tree_snapshot()

    def _resolve_path_value(self, path: list):
        val = self.raw_json_data
        for key in path:
            if isinstance(val, list):
                try:
                    val = val[int(key)]
                except ValueError:
                    val = val[key]
            else:
                val = val[key]
        return val

    def _get_selected_watch_path_str(self) -> str | None:
        if not hasattr(self, "table"):
            return None
        try:
            row_index = self.table.cursor_row
            if row_index is None:
                return None
            cell_value = self.table.get_cell_at((row_index, 0))
            if cell_value is None:
                return None
            return str(cell_value)
        except Exception:
            return None

    def _get_selected_tree_node(self):
        tree = self.query_one("#inspector-tree", Tree)
        return tree.cursor_node

    def _show_popup(self, title: str, value) -> None:
        if isinstance(value, (dict, list)):
            body = json.dumps(value, indent=2, ensure_ascii=False)
        else:
            body = str(value)
        self.push_screen(ValuePopup(title, body))

    def update_watch_window(self) -> None:
        if not self.raw_json_data or not hasattr(self, "table") or self.value_col is None:
            return

        for path in self.watched_paths:
            path_str = ".".join(path)
            try:
                val = self._resolve_path_value(path)
                if isinstance(val, (dict, list)):
                    full_text = json.dumps(val, ensure_ascii=False)
                    display_val = full_text[:120] + ("..." if len(full_text) > 120 else "")
                else:
                    display_val = str(val)
                self.table.update_cell(path_str, self.value_col, display_val)
            except (KeyError, IndexError, ValueError, TypeError):
                self.table.update_cell(path_str, self.value_col, "N/A or Error")

    def action_refresh_tree(self) -> None:
        self.refresh_tree_snapshot()

    def refresh_tree_snapshot(self) -> None:
        if not self.raw_json_data:
            return

        tree = self.query_one("#inspector-tree", Tree)
        tree.clear()
        tree.root.label = "Gamestate Snapshot"
        tree.root.expand()
        self._populate_node(tree.root, self.raw_json_data, path=[])
        self.update_log_system("Tree snapshot refreshed.")

    def _populate_node(self, parent_node: TreeNode, data, path: list) -> None:
        if isinstance(data, dict):
            for k, v in data.items():
                current_path = path + [str(k)]
                if isinstance(v, (dict, list)):
                    label = f"{k} {{}}" if isinstance(v, dict) else f"{k} [{len(v)}]"
                    parent_node.add(label, data={"value": v, "loaded": False, "path": current_path}, allow_expand=True)
                else:
                    parent_node.add(f"{k}: {v}", data={"path": current_path, "value": v}, allow_expand=False)
        elif isinstance(data, list):
            for i, v in enumerate(data):
                current_path = path + [str(i)]
                if isinstance(v, (dict, list)):
                    label = f"[{i}] {{}}" if isinstance(v, dict) else f"[{i}] [{len(v)}]"
                    parent_node.add(label, data={"value": v, "loaded": False, "path": current_path}, allow_expand=True)
                else:
                    parent_node.add(f"[{i}]: {v}", data={"path": current_path, "value": v}, allow_expand=False)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        node = event.node
        if node.data and not node.data.get("loaded", True):
            self._populate_node(node, node.data["value"], node.data["path"])
            node.data["loaded"] = True

    def action_pin_node(self) -> None:
        tree = self.query_one("#inspector-tree", Tree)
        node = tree.cursor_node
        if node and node.data and "path" in node.data:
            self._add_watch(node.data["path"])
        else:
            self.update_log_system("Cannot pin: Highlighted node has no actionable path metadata.")

    def _add_watch(self, path: list) -> None:
        path_str = ".".join(path)
        if path not in self.watched_paths:
            self.watched_paths.append(path)
            self.table.add_row(path_str, "Pending...", key=path_str)
            self.update_log_system(f"Pinned: {path_str}")
            self.update_watch_window()
        else:
            self.update_log_system(f"Already pinned: {path_str}")

    def action_unpin_selected_watch(self) -> None:
        path_str = self._get_selected_watch_path_str()
        if not path_str:
            self.update_log_system("No watch row selected to unpin.")
            return

        for idx, path in enumerate(self.watched_paths):
            if ".".join(path) == path_str:
                del self.watched_paths[idx]
                try:
                    self.table.remove_row(path_str)
                except Exception:
                    try:
                        row_index = self.table.cursor_row
                        if row_index is not None:
                            self.table.remove_row(row_index)
                    except Exception:
                        pass
                self.update_log_system(f"Unpinned: {path_str}")
                return

        self.update_log_system(f"Could not find pinned path for selected row: {path_str}")

    def action_show_details_for_focused_widget(self) -> None:
        focused = self.focused
        if focused is None:
            self.update_log_system("No widget is focused.")
            return

        if isinstance(focused, DataTable):
            path_str = self._get_selected_watch_path_str()
            if not path_str:
                self.update_log_system("No watch row selected.")
                return
            selected_path = next((p for p in self.watched_paths if ".".join(p) == path_str), None)
            if selected_path is None:
                self.update_log_system(f"Could not resolve selected row: {path_str}")
                return
            try:
                value = self._resolve_path_value(selected_path)
            except Exception as exc:
                value = f"Failed to resolve value:\n{exc}"
            self._show_popup(f"Value for {path_str}", value)
            return

        if isinstance(focused, Tree):
            node = self._get_selected_tree_node()
            if node is None:
                self.update_log_system("No tree node selected.")
                return
            if getattr(node, "data", None) and "path" in node.data:
                path = node.data["path"]
                path_str = ".".join(path) if path else "<root>"
                try:
                    value = self._resolve_path_value(path) if path else self.raw_json_data
                except Exception:
                    value = node.data.get("value", node.label.plain if hasattr(node.label, "plain") else str(node.label))
                self._show_popup(f"Tree details: {path_str}", value)
                return
            label_text = node.label.plain if hasattr(node.label, "plain") else str(node.label)
            self._show_popup("Tree details", label_text)
            return

        self.update_log_system("Focus the Gamestate Snapshot tree or the Pinned Path table, then press 'd'.")

    def load_runtime_port(self) -> bool:
        if not RUNTIME_JSON_PATH.exists():
            self.update_log_system("runtime.json not found.")
            return False
        try:
            with open(RUNTIME_JSON_PATH, "r", encoding="utf-8") as f:
                runtime_config = json.load(f)
            port = runtime_config.get("rest_port")
            if not port:
                self.update_log_system("runtime.json configuration is missing 'rest_port'.")
                return False
            self.rest_port = port
            return True
        except Exception as exc:
            self.update_log_system(f"Failed to read runtime config: {exc}")
            return False

    def build_post_body(self, command_name: str, arg_string: str):
        arg_string = arg_string.strip()
        if not arg_string:
            return {}

        if command_name in ANSWER_OR_STR_ENDPOINTS:
            return {"answer": int(arg_string)} if arg_string.lstrip("-").isdigit() else {"str": arg_string.strip('"')}
        if command_name in FILENAME_ENDPOINTS:
            return {"filename": arg_string.strip('"')}
        if command_name in STR_ENDPOINTS:
            return {"str": arg_string.strip('"')}
        if command_name in VALUE_ENDPOINTS:
            return {"value": int(arg_string)} if arg_string.lstrip("-").isdigit() else {"value": arg_string.strip('"')}
        if command_name in ID_ONLY_ENDPOINTS:
            return {"id": int(arg_string)}
        if command_name in INTPARAM2_ONLY_ENDPOINTS:
            return {"intParam2": int(arg_string)}
        if command_name == "sell_physical_crypto":
            return {"id": int(arg_string)}
        if command_name in UNDERLYING_ENDPOINTS:
            parts = [p.strip() for p in arg_string.split(",")]
            body = {}
            if len(parts) >= 1 and parts[0]:
                body["id"] = int(parts[0])
            if len(parts) >= 2 and parts[1]:
                body["intParam2"] = int(parts[1])
            if len(parts) >= 3 and parts[2]:
                body["underlyingId"] = int(parts[2])
            return body
        if command_name in ID_INTPARAM2_ENDPOINTS:
            parts = [p.strip() for p in arg_string.split(",")]
            body = {}
            if len(parts) >= 1 and parts[0]:
                body["id"] = int(parts[0])
            if len(parts) >= 2 and parts[1]:
                body["intParam2"] = int(parts[1])
            return body
        if command_name == "nav_set_history":
            return json.loads(arg_string)
        if command_name == "set_custom_data":
            return json.loads(arg_string)
        if arg_string.lstrip("-").isdigit():
            return {"id": int(arg_string)}
        return {"str": arg_string.strip('"')}

    def perform_request(self, method: str, path: str, json_body=None):
        if is_wsl:
            msg = {
                "method": method,
                "path": f"/{path.lstrip('/')}",
            }
            if method != "GET" and json_body is not None:
                msg["json"] = json_body

            with self.bridge_lock:
                if proc.stdin is None or proc.stdout is None:
                    raise RuntimeError("bridge process stdio is unavailable")

                proc.stdin.write(json.dumps(msg) + "\n")
                proc.stdin.flush()

                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError("helper exited or produced no output")

            result = json.loads(line)
            if not isinstance(result, dict):
                raise RuntimeError(f"bridge returned non-object response: {result!r}")
            return result

        if not self.rest_port:
            if not self.load_runtime_port():
                raise RuntimeError("Connection port missing.")

        url = f"http://127.0.0.1:{self.rest_port}/{path.lstrip('/')}"
        with httpx.Client(timeout=5.0) as client:
            if method == "GET":
                response = client.get(url, headers={"Content-Type": "application/json"})
            else:
                response = client.post(url, json=json_body)

        try:
            body = response.json()
        except Exception:
            body = response.text

        return {
            "ok": response.is_success,
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }

    def on_autocomplete_input_control_key(self, message: AutocompleteInput.ControlKey) -> None:
        opt_list = self.query_one("#autocomplete_list", OptionList)
        input_widget = self.query_one("#command_input", AutocompleteInput)

        if opt_list.styles.display == "block":
            if message.action == "up":
                if opt_list.highlighted is not None and opt_list.highlighted > 0:
                    opt_list.highlighted -= 1
            elif message.action == "down":
                if opt_list.highlighted is not None and opt_list.highlighted < len(self.current_matches) - 1:
                    opt_list.highlighted += 1
            elif message.action == "tab":
                if opt_list.highlighted is not None and opt_list.highlighted < len(self.current_matches):
                    selected_cmd = self.current_matches[opt_list.highlighted]
                    current_parts = input_widget.value.strip().split(maxsplit=1)
                    args_suffix = f" {current_parts[1]}" if len(current_parts) > 1 else ""
                    input_widget.value = f"{selected_cmd}{args_suffix}"
                    input_widget.cursor_position = len(input_widget.value)
                    opt_list.styles.display = "none"
        else:
            if message.action == "up":
                if not self.command_history:
                    return
                if self.history_pointer == -1:
                    self.temporary_input_buffer = input_widget.value
                    self.history_pointer = len(self.command_history) - 1
                elif self.history_pointer > 0:
                    self.history_pointer -= 1
                input_widget.value = self.command_history[self.history_pointer]
                input_widget.cursor_position = len(input_widget.value)
            elif message.action == "down":
                if self.history_pointer == -1:
                    return
                if self.history_pointer < len(self.command_history) - 1:
                    self.history_pointer += 1
                    input_widget.value = self.command_history[self.history_pointer]
                else:
                    self.history_pointer = -1
                    input_widget.value = self.temporary_input_buffer
                input_widget.cursor_position = len(input_widget.value)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option:
            input_widget = self.query_one("#command_input", AutocompleteInput)
            input_widget.value = str(event.option.prompt)
            input_widget.focus()
            self.query_one("#autocomplete_list", OptionList).styles.display = "none"

    def append_log(self, message: str) -> None:
        self.log_lines.append(message)
        if len(self.log_lines) > 200:
            self.log_lines.pop(0)
        self.update_log()

    def update_log_system(self, message: str) -> None:
        self.append_log(f"[System] {message}")

    def update_log(self) -> None:
        log_widget = self.query_one("#log", Static)
        log_widget.update("\n".join(self.log_lines))
        self.query_one("#log-container", VerticalScroll).scroll_end(animate=False)

    async def process_and_send_command(self, raw_input: str) -> None:
        parts = raw_input.split(maxsplit=1)
        command_name = parts[0]
        arg_string = parts[1] if len(parts) > 1 else ""
        method = "GET" if command_name in GET_ONLY_ENDPOINTS else "POST"

        json_body = {}
        if method == "POST":
            try:
                json_body = self.build_post_body(command_name, arg_string)
            except Exception as exc:
                self.update_log_system(f"Bad arguments for {command_name}: {exc}")
                return
            self.append_log("sending JSON body: " + json.dumps(json_body))

        def send_request():
            return self.perform_request(method, command_name, json_body)

        try:
            worker = self.run_worker(send_request, thread=True)
            response = await worker.wait()

            if not response.get("ok"):
                error_body = response.get("body")
                self.update_log_system(
                    f"API Error ({response.get('status', 'unknown')}): {error_body}"
                )
                return

            self.update_log_system(
                f"Endpoint response: {json.dumps(response.get('body'), ensure_ascii=False)}"
            )
            self.force_poll_flag = True

        except Exception as exc:
            self.update_log_system(f"Command routing failed: {exc}")

    async def _auto_close_modal(self) -> None:
        await self.process_and_send_command("close_modal")

    def persistent_gamestate_loop(self) -> None:
        while True:
            try:
                result = self.perform_request("GET", "gamestate")
            except Exception as exc:
                self.call_from_thread(self.update_log_system, f"Gamestate poll failed: {exc}")
                time.sleep(2.0)
                continue

            if not result.get("ok"):
                self.call_from_thread(
                    self.update_log_system,
                    f"Gamestate poll failed with status {result.get('status')}: {result.get('body')}"
                )
                time.sleep(2.0)
                continue

            body = result.get("body")

            if isinstance(body, (dict, list)):
                raw_text = json.dumps(body, ensure_ascii=False)
                payload = body
            else:
                raw_text = str(body)
                try:
                    payload = json.loads(raw_text)
                except Exception as exc:
                    self.call_from_thread(
                        self.update_log_system,
                        f"Failed to parse gamestate payload: {exc}"
                    )
                    self.sleep_or_wait()
                    continue

            modal_match = MODAL_TEXT_REGEX.search(raw_text)
            modal_type_match = MODAL_TYPE_REGEX.search(raw_text)
            extracted_modal = None
            modal_type = None

            if modal_type_match:
                modal_type = int(modal_type_match.group(1))
            if modal_match:
                extracted_modal = modal_match.group(1).encode().decode("unicode_escape")

            if modal_type is not None or extracted_modal:
                type_suffix = f" type {modal_type}" if modal_type is not None else ""
                if (
                    (extracted_modal and extracted_modal != self.last_seen_modal_text)
                    or modal_type != self.last_seen_modal_type
                ):
                    self.last_seen_modal_text = extracted_modal or ""
                    self.last_seen_modal_type = modal_type
                    self.call_from_thread(
                        self.append_log,
                        f"[Game Modal Alert{type_suffix}]: {extracted_modal or '<no text>'}"
                    )
                if modal_type == 4:
                    self.call_from_thread(self.append_log, "Auto-closing modal of type 4")
                    self.call_from_thread(self._auto_close_modal)
            else:
                self.last_seen_modal_text = ""
                self.last_seen_modal_type = None

            if raw_text == self.last_raw_payload:
                self.sleep_or_wait()
                continue

            self.last_raw_payload = raw_text

            try:
                self.call_from_thread(self._handle_new_gamestate, payload)
            except Exception as exc:
                self.call_from_thread(
                    self.update_log_system,
                    f"Failed to process gamestate payload: {exc}"
                )

            self.sleep_or_wait()

    def sleep_or_wait(self) -> None:
        for _ in range(20):
            if self.force_poll_flag:
                self.force_poll_flag = False
                break
            time.sleep(0.1)


if __name__ == "__main__":
    WSRTextualApp().run()
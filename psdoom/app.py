"""
Main application module for PSDoom.
"""

from typing import List, Dict
import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, DataTable, Static
from textual.reactive import reactive
from textual.binding import Binding

from psdoom.process_manager import ProcessManager


class ProcessKillScreen(Static):
    """Screen shown when killing a process."""
    
    DEFAULT_CSS = """
    ProcessKillScreen {
        width: 100%;
        height: 100%;
        background: rgba(15, 0, 0, 0.85);
        align: center middle;
    }
    
    #kill-container {
        width: 50%;
        height: 15;
        background: #333333;
        padding: 1 2;
        border: thick #cc0000;
    }
    
    #kill-container Static {
        text-align: center;
        margin-bottom: 1;
    }
    """
    
    def __init__(self, pid: int, process_name: str):
        super().__init__()
        self.pid = pid
        self.process_name = process_name
        
    def compose(self) -> ComposeResult:
        with Container(id="kill-container"):
            yield Static(f"[bold red]KILLING PROCESS[/]")
            yield Static(f"PID: {self.pid}")
            yield Static(f"Name: {self.process_name}")
            yield Static("[blink]* * * KABOOM * * *[/blink]")

    async def on_mount(self) -> None:
        await asyncio.sleep(2)
        self.remove()


class PSDoomApp(App):
    """The main PSDoom application."""
    
    TITLE = "PSDoom - Terminal Process Manager"
    SUB_TITLE = "Kill processes Doom-style!"
    
    DEFAULT_CSS = """
    Screen {
        background: #202020;
    }
    
    #main {
        height: 100%;
        margin: 0 1;
        layout: vertical;
    }
    
    #search-container {
        height: 3;
        margin-bottom: 1;
        align-vertical: middle;
    }
    
    #search-label {
        color: #aaaaaa;
        text-style: bold;
        width: auto;
        padding-right: 1;
        margin-top: 1;
    }
    
    #search-input {
        width: 100%;
        background: #333333;
        color: #ffffff;
        border: solid #777777;
    }
    
    #process-table {
        height: 1fr;
        width: 100%;
        margin-bottom: 1;
        border: solid #555555;
    }
    
    .datatable--header {
        background: #444444;
        color: #ffffff;
    }
    
    .datatable--cursor {
        background: #666666;
    }
    
    .datatable--hover {
        background: #444444;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("ctrl+k", "kill", "Kill"),
        Binding("escape", "focus_table", "Table"),
        Binding("s", "focus_search", "Search"),
    ]
    
    search_term = reactive("")
    selected_pid = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
    
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        
        with Container(id="main"):
            with Horizontal(id="search-container"):
                yield Static("Search:", id="search-label")
                yield Input(placeholder="Type to filter processes...", id="search-input")
            
            yield DataTable(id="process-table")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        # Set up the table
        table = self.query_one("#process-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("PID", "Name", "Command", "Status")
        
        # Set column widths for better display
        table.column_widths = {
            0: 7,      # PID column
            1: 20,     # Name column
            2: 100,    # Command column (much more space)
            3: 10      # Status column
        }
        
        # Make table focusable and focus it by default
        table.can_focus = True
        table.focus()
        
        self.refresh_process_list()
    
    def refresh_process_list(self) -> None:
        """Refresh the process list based on current search term."""
        self.process_manager.refresh()
        
        # Filter to only show current user's processes
        current_username = self.process_manager.get_current_username()
        processes = [
            p for p in self.process_manager.filter_processes(self.search_term) 
            if p.get('username') == current_username
        ]
        
        table = self.query_one("#process-table", DataTable)
        table.clear()
        
        for process in processes:
            pid = str(process.get('pid', ''))
            name = process.get('name', '')
            
            # Truncate command line for display
            cmdline = process.get('cmdline', '')
            if len(cmdline) > 80:
                cmdline = cmdline[:77] + "..."
                
            status = process.get('status', '')
            
            table.add_row(pid, name, cmdline, status)
    
    def action_refresh(self) -> None:
        """Refresh the process list."""
        self.refresh_process_list()
    
    @on(Input.Changed, "#search-input")
    def on_search_input_changed(self, event: Input.Changed) -> None:
        """Update the search term when the input changes."""
        self.search_term = event.value
        self.refresh_process_list()
        
    @on(Input.Submitted, "#search-input")
    def on_search_input_submitted(self, event: Input.Submitted) -> None:
        """When search is submitted, focus back on the process table."""
        self.query_one("#process-table").focus()
    
    def action_focus_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one("#search-input", Input)
        self.set_focus(search_input)
    
    def action_focus_table(self) -> None:
        """Focus the process table."""
        table = self.query_one("#process-table", DataTable)
        table.focus()
    
    def action_reset_search(self) -> None:
        """Clear search and return focus to the table."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.search_term = ""
        self.refresh_process_list()
        self.query_one("#process-table").focus()
    
    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        row = event.data_table.get_row(event.row_key)
        if row:
            self.selected_pid = int(row[0])
            details = f"Selected: [bold]{row[1]}[/] (PID: {row[0]}) - Press [bold red]'ctrl+k'[/] to kill"
    
    def action_kill(self) -> None:
        """Kill the selected process."""
        table = self.query_one("#process-table", DataTable)
        if table.cursor_row is not None:
            # Get PID from the current cursor row
            pid_str = table.get_cell_at((table.cursor_row, 0))
            if pid_str and pid_str.isdigit():
                self.selected_pid = int(pid_str)
                # Find process name
                for proc in self.process_manager.filter_processes():
                    if proc['pid'] == self.selected_pid:
                        proc_name = proc.get('name', 'Unknown')
                        kill_screen = ProcessKillScreen(self.selected_pid, proc_name)
                        self.mount(kill_screen)
                        success = self.process_manager.kill_process(self.selected_pid)
                        
                        # Refresh after kill
                        asyncio.create_task(self.delayed_refresh())
                        break
    
    def action_select_item(self) -> None:
        """Select the current process for more information."""
        table = self.query_one("#process-table", DataTable)
        if table.cursor_row is not None:
            # Get process details for the selected row
            pid_str = table.get_cell_at((table.cursor_row, 0))
            if pid_str and pid_str.isdigit():
                pid = int(pid_str)
                process_info = self.process_manager.get_process_info(pid)
                if process_info:
                    details = f"PID: {pid}\n"
                    details += f"Name: {process_info.get('name', 'Unknown')}\n"
                    details += f"User: {process_info.get('username', 'Unknown')}\n"
                    details += f"Status: {process_info.get('status', 'Unknown')}\n"
                    details += f"Command: {process_info.get('cmdline', 'Unknown')}\n"
                    # self.query_one("#process-details", Static).update(details)
    
    async def delayed_refresh(self) -> None:
        """Refresh the process list after a short delay."""
        await asyncio.sleep(2)
        self.refresh_process_list()


def main():
    """Entry point for the application."""
    app = PSDoomApp()
    app.run()


if __name__ == "__main__":
    main()

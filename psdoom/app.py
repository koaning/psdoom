"""
Main application module for PSDoom.
"""

from typing import List, Dict
import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, DataTable, Static, Button
from textual.events import Key
from textual.reactive import reactive
from textual.binding import Binding
from textual.keys import Keys

from psdoom.process_manager import ProcessManager


# We'll replace the kill screen with notifications


class PSDoomApp(App):
    """The main PSDoom application."""
    
    TITLE = "PSDoom - Terminal Process Manager"
    SUB_TITLE = "Kill processes"
    
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
        # Remove 'q' binding since Ctrl+Q conflicts with other apps
        # We'll handle exit with Ctrl+C instead
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "focus_table", "Table"),
        Binding("s", "focus_search", "Search"),
        # Add the k shortcut that will show in the footer all the time
        Binding("k", "kill", "Kill Process"),
        # Add enter key for selecting rows
        Binding("enter", "select_item", "Select Process"),
    ]
    
    search_term = reactive("")
    selected_pid = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
        self.last_ctrl_c_time = 0  # Track time of last Ctrl+C press
    
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
        
        # Make table focusable
        table.can_focus = True
        
        # The 'k' key info is already in the subtitle
        # No need to change it dynamically
        
        # Initial process list
        self.refresh_process_list()
        
        # Focus the search input on startup
        self.query_one("#search-input", Input).focus()
        

    
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
            # Update footer message when a process is selected
            proc_name = row[1]
            pid = row[0]
            self.notify(f"Selected: {proc_name} (PID: {pid}) - Press 'k' to kill", timeout=3)
    
    @on(Key)
    def on_key(self, event: Key) -> None:
        """Handle key press events."""
        # Check if focused on the table and handle the 'k' key directly
        table = self.query_one("#process-table", DataTable)
        if self.focused == table and event.key == "k":
            event.prevent_default()
            event.stop()
            self.action_kill()
        
        # Implement double Ctrl+C to exit
        if event.key == "ctrl+c":
            event.prevent_default()
            event.stop()
            
            current_time = asyncio.get_event_loop().time()
            # If pressed twice within 1 second, exit
            if current_time - self.last_ctrl_c_time < 1.0:
                self.exit()
            else:
                self.notify("Press Ctrl+C again to exit")
                self.last_ctrl_c_time = current_time
                
    # We'll handle the 'k' key directly in the on_key method instead
    # of trying to dynamically update bindings
    
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
                        
                        # Start the process kill sequence with notifications
                        asyncio.create_task(self.kill_process_with_notifications(self.selected_pid, proc_name))
                        break
    
    async def kill_process_with_notifications(self, pid: int, proc_name: str) -> None:
        """Kill a process with status notifications."""
        # Initial notification - red for warning
        self.notify(f"[bold red]KILLING PROCESS: {proc_name} (PID: {pid})[/]", timeout=3)
        await asyncio.sleep(0.5)
        
        # Send status notifications
        self.notify("[red]Initiating process termination...[/]", timeout=2)
        await asyncio.sleep(0.7)
        
        self.notify("[red]Sending SIGTERM signal...[/]", timeout=2)
        await asyncio.sleep(0.8)
        
        # Actually kill the process here
        success = self.process_manager.kill_process(pid)
        
        self.notify("[yellow]Waiting for process to terminate...[/]", timeout=2)
        await asyncio.sleep(1)
        
        # Show the kaboom animation
        self.notify("[bold red blink]* * * KABOOM * * *[/]", timeout=3)
        await asyncio.sleep(1)
        
        # Final success notification - green for success
        if success:
            self.notify(f"[bold green]Process {proc_name} (PID: {pid}) terminated successfully![/]", timeout=5)
        else:
            self.notify(f"[bold orange]Warning: Process {proc_name} (PID: {pid}) may not have terminated correctly[/]", timeout=5)
        
        # Refresh process list
        await self.delayed_refresh()
    
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

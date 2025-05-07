"""
Process management functionality for PSDoom.
"""

import psutil
from pathlib import Path
import signal
from typing import Dict, List, Optional


class ProcessManager:
    """Manages the listing, filtering, and termination of system processes."""
    
    def __init__(self):
        """Initialize the process manager."""
        self.refresh()
        
    def refresh(self) -> None:
        """Refresh the list of running processes."""
        self.processes = {}
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline', 'status']):
            try:
                self.processes[proc.info['pid']] = proc.info
                # Convert cmdline list to a string for display
                if self.processes[proc.info['pid']]['cmdline']:
                    self.processes[proc.info['pid']]['cmdline'] = ' '.join(self.processes[proc.info['pid']]['cmdline'])
                else:
                    self.processes[proc.info['pid']]['cmdline'] = ""
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def filter_processes(self, search_term: Optional[str] = None) -> List[Dict]:
        """
        Filter processes based on a search term.
        
        Args:
            search_term: Term to search for in process name or command line
            
        Returns:
            List of matching process dictionaries
        """
        if not search_term:
            return list(self.processes.values())
            
        filtered = []
        for pid, process in self.processes.items():
            name = process.get('name', '').lower()
            cmdline = process.get('cmdline', '').lower()
            
            if (search_term.lower() in name) or (search_term.lower() in cmdline):
                filtered.append(process)
                
        return filtered
        
    def kill_process(self, pid: int) -> bool:
        """
        Kill a process by PID.
        
        Args:
            pid: Process ID to kill
            
        Returns:
            True if the process was killed successfully, False otherwise
        """
        try:
            proc = psutil.Process(pid)
            # Try SIGTERM first for a graceful shutdown
            proc.terminate()
            # Wait briefly to see if it terminates
            gone, alive = psutil.wait_procs([proc], timeout=0.5)
            if alive:
                # If still alive, use SIGKILL
                proc.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"Error killing process {pid}: {str(e)}")
            return False
            
    def get_process_info(self, pid: int) -> Optional[Dict]:
        """
        Get detailed information about a specific process.
        
        Args:
            pid: Process ID to retrieve information for
            
        Returns:
            Dictionary with process details or None if process not found
        """
        return self.processes.get(pid)
        
    def get_current_username(self) -> str:
        """
        Get the username of the current user.
        
        Returns:
            String with the current username
        """
        import getpass
        return getpass.getuser()

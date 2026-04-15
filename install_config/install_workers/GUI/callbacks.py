# install_config/install_workers/GUI/callbacks.py

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import os
import logging

# Import helper functions if they are moved here from widgets.py
# from .widgets import _handle_focus_in, _handle_focus_out

# Keep pyperclip fallback if used
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Note: All functions now receive 'app' (the InstallerApp instance) as first argument.

# --- Target Project Directory Callback ---
def browse_target_project_dir(app):
    """Handles browsing for the target project directory."""
    root_ref = getattr(app, 'root', None)
    target_var_ref = getattr(app, 'target_project_dir_var', None)
    messagebox_ref = getattr(app, 'messagebox', messagebox)

    if not root_ref or not target_var_ref:
        if hasattr(app, 'log_message_action'):
            app.log_message_action("Critical attribute missing: root or target_project_dir_var.", logging.CRITICAL)
        return

    dirpath = filedialog.askdirectory(
        parent=root_ref,
        title="Select Your Target Project Directory",
        mustexist=True
    )

    if not dirpath:
        app.log_message_action("Target project directory selection cancelled.", logging.DEBUG)
        return

    resolved_path = Path(dirpath).resolve()
    if resolved_path.is_dir():
        target_var_ref.set(str(resolved_path))  # Triggers trace in gui_state
        app.log_message_action(f"Selected target project directory: {resolved_path}", logging.INFO)
    else:
        if messagebox_ref:
            messagebox_ref.showerror("Invalid Directory", f"The selected path is not a valid directory:\n{resolved_path}", parent=root_ref)
        app.log_message_action(f"Invalid target directory selected: {resolved_path}", logging.ERROR)


# --- Entrypoint Callback (Uses Target Project Dir) ---
def browse_entrypoint(app):
    """Handles browsing for the entrypoint file, relative to TARGET project dir."""
    filedialog_ref = getattr(app, 'filedialog', None)
    root_ref = getattr(app, 'root', None)
    target_project_dir_var_ref = getattr(app, 'target_project_dir_var', None)
    entrypoint_var_ref = getattr(app, 'entrypoint_var', None)
    entrypoint_entry_ref = getattr(app, 'entrypoint_entry', None)
    messagebox_ref = getattr(app, 'messagebox', None)

    if not all([filedialog_ref, root_ref, target_project_dir_var_ref, entrypoint_var_ref, messagebox_ref]):
         print("ERROR: Application object missing required attributes for browse_entrypoint.")
         if hasattr(app, 'log_message_action'):
            app.log_message_action("ERROR: Critical attributes missing for browse_entrypoint.", logging.CRITICAL)
         return

    target_project_root = target_project_dir_var_ref.get()
    if not target_project_root or not Path(target_project_root).is_dir():
        messagebox_ref.showerror("Error", "Please select a valid Target Project Directory first.", parent=root_ref)
        app.log_message_action("Browse entrypoint attempted before target directory selected.", logging.WARNING)
        return

    filepath = filedialog_ref.askopenfilename(
        parent=root_ref,
        initialdir=target_project_root,
        title="Select Entrypoint Script (within Target Project)",
        filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
    )
    if filepath:
        try:
            entry_path = Path(filepath).resolve()
            project_root_path = Path(target_project_root).resolve()

            # Check using is_relative_to
            if entry_path.is_file() and entry_path.is_relative_to(project_root_path):
                 relative_path = entry_path.relative_to(project_root_path)
                 entrypoint_var_ref.set(str(relative_path))
                 if entrypoint_entry_ref:
                     entrypoint_entry_ref.config(foreground='black', style="TEntry") # Reset style
                 app.log_message_action(f"Selected entrypoint: {relative_path}", logging.INFO)
            else:
                 if not entry_path.is_file(): # Check if selected path is actually a file
                    messagebox_ref.showerror("Invalid Selection", f"The selected path is not a file:\n'{filepath}'", parent=root_ref)
                    app.log_message_action(f"Selected entrypoint path is not a file: '{filepath}'.", logging.ERROR)
                 else: # Otherwise, it's not relative
                    messagebox_ref.showerror("Error", f"File must be inside selected Target Project Directory\n('{project_root_path}')", parent=root_ref)
                    app.log_message_action(f"Selected entrypoint '{filepath}' is not relative to target project root '{project_root_path}'.", logging.ERROR)

        except ValueError:
             messagebox_ref.showerror("Error", f"Path mismatch (e.g., different drive) or invalid path. File must be inside Target Project Directory\n('{project_root_path}')", parent=root_ref)
             app.log_message_action(f"Selected entrypoint '{filepath}' failed relative path calculation (ValueError).", logging.ERROR)
        except Exception as e:
             messagebox_ref.showerror("Error", f"An error occurred processing the path: {e}", parent=root_ref)
             app.log_message_action(f"Error browsing entrypoint: {e}", logging.ERROR)

# --- Other Browse Callbacks ---
def browse_docker_path(app):
    """Handles browsing for the Docker executable."""
    filedialog_ref = getattr(app, 'filedialog', None)
    root_ref = getattr(app, 'root', None)
    docker_path_var_ref = getattr(app, 'docker_path_var', None)
    if not all([filedialog_ref, root_ref, docker_path_var_ref]): return

    initial_dir = "C:/Program Files/Docker/Docker/resources/bin" if os.name == 'nt' else "/usr/bin"
    filetypes = [("Docker Executable", "docker.exe"), ("All Files", "*.*")] if os.name == 'nt' else [("Docker", "docker"), ("All Files", "*.*")]

    filepath = filedialog_ref.askopenfilename(
        parent=root_ref,
        initialdir=initial_dir,
        title="Select Docker Executable",
        filetypes=filetypes
    )
    if filepath and Path(filepath).is_file(): # Add check if file exists
        docker_path_var_ref.set(filepath)
        app.log_message_action(f"Selected Docker path: {filepath}", logging.INFO)
    elif filepath: # User selected something, but it's not a file
         if hasattr(app, 'messagebox'):
             app.messagebox.showwarning("Invalid Path", f"Selected Docker path is not a valid file:\n{filepath}", parent=root_ref)
         app.log_message_action(f"Invalid Docker path selected (not a file): {filepath}", logging.WARNING)


def browse_xwindows_path(app):
    """Handles browsing for the Xwindows (VcXsrv) executable."""
    filedialog_ref = getattr(app, 'filedialog', None)
    root_ref = getattr(app, 'root', None)
    xwindows_path_var_ref = getattr(app, 'xwindows_path_var', None)
    if not all([filedialog_ref, root_ref, xwindows_path_var_ref]): return

    initial_dir = "C:/Program Files/VcXsrv" if os.name == 'nt' else "/"
    filetypes = [("VcXsrv Executable", "vcxsrv.exe"), ("All Files", "*.*")] if os.name == 'nt' else [("All Files", "*.*")]

    filepath = filedialog_ref.askopenfilename(
        parent=root_ref,
        initialdir=initial_dir,
        title="Select Xwindows (VcXsrv) Executable",
        filetypes=filetypes
    )
    if filepath and Path(filepath).is_file(): # Add check if file exists
        xwindows_path_var_ref.set(filepath)
        app.log_message_action(f"Selected Xwindows path: {filepath}", logging.INFO)
    elif filepath: # User selected something, but it's not a file
        if hasattr(app, 'messagebox'):
            app.messagebox.showwarning("Invalid Path", f"Selected VcXsrv path is not a valid file:\n{filepath}", parent=root_ref)
        app.log_message_action(f"Invalid VcXsrv path selected (not a file): {filepath}", logging.WARNING)


# --- Focus Handlers (Keep separate or use helpers from widgets.py) ---
# Using helpers from widgets.py is cleaner, these are placeholders if needed directly
def on_entry_focus_in(app, event):
    """Placeholder: Logic moved to _handle_focus_in in widgets.py"""
    logger.debug(f"Focus In event on {event.widget}")
    pass

def on_entry_focus_out(app, event):
    """Placeholder: Logic moved to _handle_focus_out in widgets.py"""
    logger.debug(f"Focus Out event on {event.widget}")
    pass


# --- Action Callbacks ---
def copy_command(app):
    """Copies the final command to the clipboard."""
    final_frame_ref = getattr(app, 'final_frame', None)
    command_entry_ref = getattr(app, 'command_entry', None)
    root_ref = getattr(app, 'root', None)
    copy_button_ref = getattr(app, 'copy_button', None)
    messagebox_ref = getattr(app, 'messagebox', None)

    if not all([final_frame_ref, command_entry_ref, root_ref, copy_button_ref, messagebox_ref]):
        if hasattr(app, 'log_message_action'): app.log_message_action("Required component missing for copy_command.", logging.ERROR)
        else: print("ERROR: Required component missing for copy_command.")
        return
    if not final_frame_ref.winfo_ismapped(): return

    command_to_copy = command_entry_ref.get()

    if not command_to_copy:
        app.log_message_action("Command is empty, nothing to copy.", logging.WARNING)
        return

    try:
        root_ref.clipboard_clear()
        root_ref.clipboard_append(command_to_copy)
        root_ref.update()
        app.log_message_action(f"Command copied to clipboard.", logging.INFO) # Simplified log
        original_text = "Copy"
        copy_button_ref.config(text="Copied!")
        root_ref.after(1500, lambda: copy_button_ref.config(text=original_text) if root_ref.winfo_exists() and hasattr(copy_button_ref, 'winfo_exists') and copy_button_ref.winfo_exists() else None) # Safer lambda

    except tk.TclError as e:
        app.log_message_action(f"Clipboard error (TclError): {e}", logging.ERROR)
        if PYPERCLIP_AVAILABLE:
              try:
                  pyperclip.copy(command_to_copy)
                  app.log_message_action("Copied using pyperclip.", logging.INFO)
                  if copy_button_ref:
                      copy_button_ref.config(text="Copied!")
                      root_ref.after(1500, lambda: copy_button_ref.config(text="Copy") if root_ref.winfo_exists() and hasattr(copy_button_ref, 'winfo_exists') and copy_button_ref.winfo_exists() else None) # Safer lambda
              except Exception as pe:
                  app.log_message_action(f"Pyperclip fallback failed: {pe}", logging.ERROR)
                  messagebox_ref.showwarning("Warning", f"Auto-copy failed.\nTkinter error: {e}\nPyperclip error: {pe}", parent=root_ref)
        else:
             messagebox_ref.showwarning("Warning", f"Auto-copy failed (Tkinter error: {e}).\nPyperclip not available for fallback.", parent=root_ref)
    except Exception as e_generic:
         app.log_message_action(f"Unexpected copy error: {e_generic}", logging.ERROR)
         messagebox_ref.showwarning("Warning", f"Auto-copy failed: {e_generic}", parent=root_ref)


def copy_log_content(app):
    """Copies the entire content of the log area."""
    log_area_ref = getattr(app, 'log_area', None)
    root_ref = getattr(app, 'root', None)
    messagebox_ref = getattr(app, 'messagebox', None)

    if not all([log_area_ref, root_ref]):
        if hasattr(app, 'log_message_action'): app.log_message_action("Log area widget or root not found.", logging.ERROR)
        else: print("Log area widget or root not found.")
        return

    original_state = None
    try:
        original_state = log_area_ref.cget('state')
        log_area_ref.config(state=tk.NORMAL) # Temporarily enable
        log_content = log_area_ref.get("1.0", tk.END).strip()
        log_area_ref.config(state=original_state) # Restore original state

        if log_content:
            root_ref.clipboard_clear()
            root_ref.clipboard_append(log_content)
            root_ref.update()
            app.log_message_action("Log copied.", logging.INFO)
        else:
            app.log_message_action("Log empty, nothing to copy.", logging.INFO)

    except Exception as e:
        # Ensure state is restored even if error occurs
        if log_area_ref and original_state:
             try:
                 if log_area_ref.winfo_exists(): # Check if widget still exists
                    log_area_ref.config(state=original_state)
             except Exception as restore_e:
                 print(f"Error restoring log area state: {restore_e}")
        app.log_message_action(f"Log copy failed: {e}", logging.ERROR)
        if messagebox_ref: messagebox_ref.showerror("Error", f"Log copy failed:\n{e}", parent=root_ref)


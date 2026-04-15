# install_config/install_workers/GUI/widgets.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging

logger = logging.getLogger(__name__)

def setup_styles():
    """Configures ttk styles for the application."""
    style = ttk.Style()
    # Attempt to use a modern theme if available
    preferred_themes = ['vista', 'xpnative', 'clam', 'alt', 'default']
    for theme in preferred_themes:
        if theme in style.theme_names():
            try:
                style.theme_use(theme)
                logger.info(f"Using theme: {theme}")
                break
            except tk.TclError:
                continue
    else:
        logger.warning("Could not set preferred theme, using default.")

    try:
        # Configure styles for specific widgets
        style.configure("TButton", padding=6, font=('Segoe UI', 9))
        style.configure("TEntry", padding=(5, 5), font=('Segoe UI', 9))
        style.configure("TLabel", padding=(0, 2), font=('Segoe UI', 9))
        style.configure("TCheckbutton", padding=(0, 2), font=('Segoe UI', 9))
        style.configure("TLabelframe", padding="5 5 5 5")
        style.configure("TLabelframe.Label", font=('Segoe UI', 9, 'bold'))
        style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'))
        style.configure("red.Horizontal.TProgressbar", background='#f44336') # Example progress bar colors
        style.configure("green.Horizontal.TProgressbar", background='#4caf50')
        # Style for placeholder text in Entry widgets
        style.configure("Placeholder.TEntry", foreground='grey', font=('Segoe UI', 9))
        # Ensure disabled Entry text is also greyed out
        style.map("TEntry", foreground=[('disabled', 'grey')])
    except tk.TclError as e:
        logger.error(f"Failed to configure some ttk styles: {e}")
    return style

# --- Placeholder Handling for Entry Widgets ---
def _set_placeholder(widget: ttk.Entry, text: str, placeholder: str):
    """Sets or removes placeholder text in an Entry widget."""
    if not text or text == placeholder: # Check if current text is empty or already the placeholder
        widget.delete(0, tk.END)
        widget.insert(0, placeholder)
        widget.config(style="Placeholder.TEntry") # Apply placeholder style
    else:
        # If there's actual text, ensure normal style is applied
        if widget.cget("style") == "Placeholder.TEntry":
             widget.config(style="TEntry")

def _handle_focus_in(event, placeholder):
    """Removes placeholder text when Entry gains focus."""
    widget = event.widget
    if isinstance(widget, ttk.Entry) and widget.get() == placeholder:
        widget.config(style="TEntry") # Switch to normal style
        widget.delete(0, tk.END)

def _handle_focus_out(app, event, placeholder, var_name):
    """Restores placeholder text if Entry loses focus and is empty."""
    widget = event.widget
    var = getattr(app, var_name, None)
    # Check if the variable exists and its value is empty
    if isinstance(widget, ttk.Entry) and var and not var.get():
        _set_placeholder(widget, "", placeholder)

# --- Main Widget Creation Function ---
def create_all_widgets(app):
    """Creates and grids all the main widgets for the InstallerApp."""
    root = app.root
    # Get icon display size from app instance, fallback to default
    icon_w, icon_h = getattr(app, 'icon_display_size', (48, 48))

    # Configure root window grid weights
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=0)  # Header row
    root.rowconfigure(1, weight=0)  # Separator row
    root.rowconfigure(2, weight=1)  # Main content row (allow expansion)

    # --- Header ---
    header = ttk.Frame(root, padding="10 5")
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(1, weight=1) # Allow label to expand
    # Display PNG icon if available
    if hasattr(app, 'png_icon') and app.png_icon:
        try: # Add try-except for robustness
            canvas = tk.Canvas(header, width=icon_w, height=icon_h, borderwidth=0, highlightthickness=0)
            canvas.create_image(0, 0, image=app.png_icon, anchor=tk.NW)
            canvas.image = app.png_icon # Keep reference
            canvas.grid(row=0, column=0, padx=(0, 10), pady=(0, 5))
        except Exception as e:
            logger.error(f"Failed to display header icon: {e}")
    # Display application title
    ttk.Label(header, text=f"{getattr(app, 'BDR_FOLDER_NAME', 'Installer')} Installer", style="Header.TLabel")\
        .grid(row=0, column=1, sticky="w")

    # --- Separator ---
    ttk.Separator(root, orient=tk.HORIZONTAL).grid(row=1, column=0, sticky="ew", padx=10, pady=5)

    # --- Main Content Frame ---
    main = ttk.Frame(root, padding=10)
    main.grid(row=2, column=0, sticky="nsew") # Fill available space
    main.columnconfigure(0, weight=1) # Allow content column to expand
    # Adjust row weights for desired vertical distribution
    main.rowconfigure(0, weight=0) # Target Frame
    main.rowconfigure(1, weight=0) # Config Frame
    main.rowconfigure(2, weight=0) # Options Frame
    main.rowconfigure(3, weight=0) # Log Label
    main.rowconfigure(4, weight=1) # Log Area (allow expansion)
    main.rowconfigure(5, weight=0) # Progress Bar
    main.rowconfigure(6, weight=0) # Final Command Frame (hidden initially)
    main.rowconfigure(7, weight=0) # Buttons Frame

    # --- Target Project Directory Frame ---
    target = ttk.LabelFrame(main, text="Target Project Directory", padding="10 5")
    target.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    target.columnconfigure(0, weight=1) # Allow entry field to expand
    placeholder_target = "Select the root folder of your project..."
    # Ensure target_project_dir_var exists on app object
    app.target_project_dir_entry = ttk.Entry(target, width=70, textvariable=app.target_project_dir_var)
    _set_placeholder(app.target_project_dir_entry, app.target_project_dir_var.get(), placeholder_target)
    app.target_project_dir_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    # Bind focus events for placeholder handling
    app.target_project_dir_entry.bind("<FocusIn>", lambda e: _handle_focus_in(e, placeholder_target))
    app.target_project_dir_entry.bind("<FocusOut>", lambda e: _handle_focus_out(app, e, placeholder_target, 'target_project_dir_var'))
    # Browse button
    app.target_project_browse_button = ttk.Button(target, text="Browse...", command=app.callbacks.browse_target_project_dir)
    app.target_project_browse_button.grid(row=0, column=1, padx=(5, 5), pady=5) # Added right padding

    # --- Configuration Paths Frame ---
    config = ttk.LabelFrame(main, text="Configuration Paths", padding="10 5")
    config.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    config.columnconfigure(1, weight=1) # Allow entry fields to expand

    # Configuration entries definition
    entries = [
        ("Entrypoint Script:", 'entrypoint_entry', 'entrypoint_var', app.callbacks.browse_entrypoint, "e.g., main.py", True), # Disabled until target selected
        ("Docker Path:", 'docker_path_entry', 'docker_path_var', app.callbacks.browse_docker_path, "Path to docker.exe", False),
        ("Xwindows (VcXsrv):", 'xwindows_path_entry', 'xwindows_path_var', app.callbacks.browse_xwindows_path, "Path to vcxsrv.exe (Optional)", False)
    ]

    # Create labels, entries, and buttons for config paths
    for i, (label, attr, var, cb, placeholder, disable_initially) in enumerate(entries):
        ttk.Label(config, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        entry_var = getattr(app, var, None) # Get the Tkinter variable
        if entry_var is None: # Check if variable exists
            logger.error(f"Tkinter variable '{var}' not found on app object!")
            continue
        entry = ttk.Entry(config, width=60, textvariable=entry_var)
        _set_placeholder(entry, entry_var.get(), placeholder) # Set initial placeholder if needed
        if disable_initially:
            entry.config(state=tk.DISABLED)
        entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
        # Bind focus events for placeholder handling
        entry.bind("<FocusIn>", lambda e, p=placeholder: _handle_focus_in(e, p))
        entry.bind("<FocusOut>", lambda e, app_ref=app, p=placeholder, v=var: _handle_focus_out(app_ref, e, p, v)) # Pass app reference
        setattr(app, attr, entry) # Store widget reference on app object
        ttk.Button(config, text="Browse...", command=cb).grid(row=i, column=2, padx=5, pady=2)

    # --- Options Frame ---
    options = ttk.LabelFrame(main, text="Options", padding="10 5")
    options.grid(row=2, column=0, sticky="ew", pady=(0, 10))
    # Pack checkboxes horizontally within the options frame
    ttk.Checkbutton(options, text="Open project folder after install", variable=app.open_project_var).pack(side=tk.LEFT, padx=10, pady=5)

    # <<< ADDED CHECKBOX WIDGET >>>
    # Ensure app.force_replace_user_env_var (tk.BooleanVar) was initialized
    if hasattr(app, 'force_replace_user_env_var'):
        app.force_replace_checkbox = ttk.Checkbutton(
            options, # Parent is the options frame
            text="Replace existing project environment (.venv) if found?",
            variable=app.force_replace_user_env_var # Link to the BooleanVar
        )
        app.force_replace_checkbox.pack(side=tk.LEFT, padx=10, pady=5) # Place it next to the other one
    else:
        logger.error("'force_replace_user_env_var' not found on app object! Checkbox not created.")
    # <<< END ADDED CHECKBOX WIDGET >>>

    # --- Log Area ---
    ttk.Label(main, text="Installation Log:").grid(row=3, column=0, sticky=tk.W, pady=2)
    app.log_area = scrolledtext.ScrolledText(main, wrap=tk.WORD, height=10, state=tk.DISABLED, font=("Consolas", 9))
    app.log_area.grid(row=4, column=0, sticky="nsew", pady=(0, 5))
    # Context menu for log area
    log_menu = tk.Menu(root, tearoff=0)
    log_menu.add_command(label="Copy All", command=getattr(app.callbacks, 'copy_log_content', lambda: logger.warning("Copy log callback not found.")))
    app.log_area.bind("<Button-3>", lambda e: log_menu.post(e.x_root, e.y_root)) # Right-click binding

    # --- Progress Bar ---
    app.progress = ttk.Progressbar(main, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
    app.progress.grid(row=5, column=0, sticky="ew", pady=5)

    # --- Final Command Frame (Hidden Initially) ---
    app.final_frame = ttk.Frame(main)
    # Don't grid initially, use grid_remove() after creating widgets inside
    app.final_frame.columnconfigure(0, weight=1) # Allow entry to expand
    ttk.Label(app.final_frame, text="Run this command in your project terminal:").grid(row=0, column=0, columnspan=2, sticky=tk.W)
    app.command_entry = ttk.Entry(app.final_frame, width=70, font=("Consolas", 9), state='readonly')
    app.command_entry.grid(row=1, column=0, sticky=tk.EW, pady=2, ipady=3)
    # Ensure callback exists on app object
    copy_cmd_callback = getattr(app.callbacks, 'copy_command', lambda: logger.warning("Copy command callback not found."))
    app.copy_button = ttk.Button(app.final_frame, text="Copy", command=copy_cmd_callback, state=tk.NORMAL) # Enable copy button initially? Or only after success? Let's enable.
    app.copy_button.grid(row=1, column=1, padx=(5, 0), pady=2)
    # Grid the frame itself now, then remove it
    app.final_frame.grid(row=6, column=0, sticky="ew", pady=(5, 0))
    app.final_frame.grid_remove() # Hide it until installation completes

    # --- Buttons Frame ---
    button_frame = ttk.Frame(main)
    button_frame.grid(row=7, column=0, sticky="ew", pady=(10, 0))
    # Add weights for centering/spacing if desired, or use padding
    button_frame.columnconfigure(0, weight=0)
    button_frame.columnconfigure(1, weight=1) # Spacer
    button_frame.columnconfigure(2, weight=0)
    # Install Button
    app.install_button = ttk.Button(button_frame, text="Start Installation", command=app.on_install_button_click)
    app.install_button.grid(row=0, column=0, sticky=tk.W, padx=(0,5)) # Add padding
    # Exit/Cancel Button
    app.exit_button = ttk.Button(button_frame, text="Exit", command=app.on_closing)
    app.exit_button.grid(row=0, column=2, sticky=tk.E, padx=(5,0)) # Add padding

    logger.debug("Widgets created successfully.")
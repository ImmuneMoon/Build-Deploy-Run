# install_config/install_workers/GUI/gui_actions.py
import logging


def notify_command_ready(app):
    """Notifies the user that the deployment command is ready after installation."""
    root_ref = getattr(app, 'root', None)
    messagebox_ref = getattr(app, 'messagebox', None)

    if not all([root_ref, messagebox_ref]):
        if hasattr(app, 'log_message_action'):
            app.log_message_action("Missing root or messagebox for final command notification.", logging.WARNING)
        return

    messagebox_ref.showinfo(
        "Deployment Command Ready",
        "The deployment command has been copied to your clipboard.\n\n"
        "Run it from your project folder any time you want to rebuild.",
        parent=root_ref
    )

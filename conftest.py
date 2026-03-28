import os
import sys

# On macOS with Homebrew, add the Homebrew share directory to XDG_DATA_DIRS
# so that the xdg library can find the shared MIME database.
if sys.platform == "darwin":
    homebrew_share = "/opt/homebrew/share"
    existing = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    if homebrew_share not in existing:
        os.environ["XDG_DATA_DIRS"] = "{}:{}".format(homebrew_share, existing)

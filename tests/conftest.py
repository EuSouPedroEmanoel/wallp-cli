import os
import tempfile

os.environ["WALLP_LOG_FILE"] = os.path.join(tempfile.gettempdir(), "wallp-test.log")
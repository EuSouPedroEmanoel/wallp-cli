import os
import tempfile

os.environ["WALLPHA_LOG_FILE"] = os.path.join(tempfile.gettempdir(), "wallpha-test.log")
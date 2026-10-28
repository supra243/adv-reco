import os


os.environ.setdefault("SECRET_KEY", "development-only-secret-key-do-not-deploy")
os.environ.setdefault("DEBUG", "True")

from .base import *  # noqa: E402,F403

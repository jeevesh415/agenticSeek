"""Minimal local fallback for environments without python-dotenv."""

def load_dotenv(*_args, **_kwargs):
    return False

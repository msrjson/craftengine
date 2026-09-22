"""
Craft - a batteries-included Python web framework.

@package Craft
@author  Craft Team
"""

import sys
import os

# Set root directory in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import engine & bootstrap application
import engine
from bootstrap.app import app, asgi_app

# The ASGI application entrypoint for Uvicorn / Gunicorn / ASGI Servers
application = asgi_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("public.index:application", host="127.0.0.1", port=8000, reload=True)

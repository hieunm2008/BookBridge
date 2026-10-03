"""Production WSGI server; serve static files and terminate HTTPS in a reverse proxy."""
import os
from waitress import serve
from bookbridge.wsgi import application

if __name__ == '__main__':
    serve(application, host=os.environ.get('BOOKBRIDGE_BIND', '127.0.0.1'),
          port=int(os.environ.get('BOOKBRIDGE_PORT', '8000')), threads=4)

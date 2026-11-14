"""Cloud Run entrypoint: listen on the assigned PORT and retain Streamlit security defaults."""
import os
import sys


def command():
    port = int(os.environ.get('PORT', '8080'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535.')
    return [sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
            '--server.address=0.0.0.0', f'--server.port={port}', '--server.headless=true']


if __name__ == '__main__':
    os.execv(sys.executable, command())

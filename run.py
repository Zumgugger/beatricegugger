"""Application entry point."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)

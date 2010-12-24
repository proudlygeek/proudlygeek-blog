# Imports Flask's library
from flask import Flask

# Imports static configuration
import config

# creates the app
app = Flask(__name__)

try:
    # If config.cfg exists then override default config
    app.config.from_pyfile('../config.cfg')

except:
    # Load Default Config (see config/mode.py)
    app.config.from_object(config.DevelopmentConfig)

# Finally loads views
import views

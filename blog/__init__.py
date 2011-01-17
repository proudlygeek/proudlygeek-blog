# -*- coding: utf-8 -*-
"""

    blog
    ~~~~~~~~~~~~~~~~~~

    A simple blog app written with Flask which
    supports sqlite and Google App Engine's Datastore.

    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

# Imports Flask's library
from flask import Flask

# Imports static configuration
import config

def create_app(config_file):
    # creates the app
    app = Flask(__name__)

    try:
        # If config.cfg exists then override default config
        app.config.from_pyfile(config_file)

    except:
        # Load Default Config (see config/mode.py)
        app.config.from_object(config.DevelopmentConfig)

    return app

app = create_app('../config.cfg')

# Loading the Data Abstract Layer object
try:
    from lib import factory
    data_layer = factory(app.config['PLATFORM'])
except NameError as e:
    print e

# Finally loads views
import views

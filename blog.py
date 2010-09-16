# -*- coding: utf-8 -*-
"""

	ProudlyGeek's Blog 
	~~~~~~~~~~~~~~~~~~

	A simple blog app written with Flask and sqlite3.

	:copyright: (c) 2010 by Gianluca Bargelli.
	:license: MIT License, see LICENSE for more details.


"""
from flask import Flask, request, session, g, url_for, redirect, \
	 render_template, abort, flash

import sqlite3

# configuration
DATABASE = '/tmp/blog.db'
DEBUG = True
SECRET_KEY = 'development key'

# creates the app
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('BLOG_SETTINGS', silent = True)

def connect_db():
	"""Returns a new connection to the database."""
	return sqlite3.connect(app.config['DATABASE'])

def init_db():
	"""Creates the database tables."""
	with closing(connect_db()) as db:
		with app.open_resource('schema.sql') as f:
			db.cursor().executescript(f.read())
		db.commit()

@app.before_request
def before_request():
	"""Connects to the database before each request."""
	g.db = connect_db()


@app.after_request
def after_request(response):
	"""Closes the database again at the end of the request."""
	g.db.close()
	return response

@app.route('/')
def hello_world():
	"""This is only a test."""
	return "<h1>Hello world!</h1>"

	

if __name__=="__main__":
	app.run()

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
from contextlib import closing

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

def query_db(query, args=(), one = False):
	"""Queries the database and returns a list of dictionaries."""
	cur = g.db.execute(query, args)
	rv = [dict((cur.description[idx][0], value)
    	for idx, value in enumerate(row)) for row in cur.fetchall()]
	return (rv[0] if rv else None) if one else rv

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
def list_entries():
	entries = query_db("SELECT title, body, last_date, creation_date FROM entry")
	return render_template("list_entries.html", entries=entries)

if __name__=="__main__":
	app.run()

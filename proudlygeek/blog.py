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
import hashlib
import datetime
import re
from unicodedata import normalize
from config import mode

# creates the app
app = Flask(__name__)

try:
    # If config.cfg exists then override default config
    app.config.from_pyfile('config.cfg')

except:
    # Load Default Config (see config/mode.py)
    app.config.from_object(mode.DevelopmentConfig)


def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db(testdb=False):
    """Creates the database tables."""
    if not testdb:
        schema = 'schema.sql'
    else:
        schema = '../tests/test_db.sql'

    with closing(connect_db()) as db:
        with app.open_resource(schema) as f:
            db.cursor().executescript(f.read())
        db.commit()


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
    for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def check_password_hash(string, check):
    """
    Checks if the supplied string is equal to the password hash
    saved into the database.
    """
    stringHash = hashlib.sha224(string).hexdigest()
    if stringHash == check:
        return True
    else:
        return False


def slugify_entry(entry_title, delim=u'-'):
    """
    Creates a valid URI title by replacing whitespaces with a '-'
    and by stripping all non-words in a string (that is, only a-z
    and A-Z).
    """
    _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')
    result = []
    for word in _punct_re.split(entry_title.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


@app.before_request
def before_request():
    """
    Connects to the database before each request and
    looks up the current user.
    """
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db(
                 'SELECT user.id, user.username, rank.id, rank.role_name \
                  FROM user join rank on user.rank_id_FK = rank.id \
                  WHERE user.id = ?',
                  [session['user_id']],
                  one=True)


@app.after_request
def after_request(response):
    """Closes the database again at the end of the request."""
    g.db.close()
    return response


@app.route('/')
def list_entries():
    entries = query_db(
              'SELECT slug, title, body, last_date, creation_date \
               FROM entry')
    return render_template("list_entries.html", entries=entries)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user into the application given his credentials."""
    error = None
    if request.method == 'POST':
        user = query_db(
               'SELECT * FROM user \
                WHERE username = ?',
                [request.form['username']],
                one=True)

        if user is None:
            error = 'Invalid username'

        elif not check_password_hash(request.form['password'], \
                                     user['password']):
            error = 'Invalid password'

        else:
            session['user_id'] = user['id']
            flash('You were logged in')
            return redirect(url_for('list_entries'))

    # If the request is GET then return the login form
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logout the current user."""
    session.pop('user_id', None)
    flash("You were logged out")
    return redirect(url_for('list_entries'))


@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    """Adds a new entry."""
    if g.user:
        error = None
        if request.method == 'POST':
            if request.form['title'] is None:
                error = "The title can't be empty!"

            elif request.form['entry_text'] is None:
                error = "C'mon, write something!"

            else:
                today = datetime.date.today()
                g.db.execute(
                'INSERT INTO entry \
                 VALUES (null, ?, ?, ?, ?, null, ?)',
                (
                 slugify_entry(request.form['title']),
                 request.form['title'],
                 request.form['entry_text'],
                 today.strftime('%Y-%m-%d'),
                 g.user['id']))

                g.db.commit()
                flash('Entry added.')
                return redirect(url_for('list_entries'))

        return render_template('add_entry.html', error=error)

    return redirect(url_for('list_entries'))


@app.route('/articles/<int:year>/<int:month>/<int:day>/<title>')
def view_entry(year, month, day, title):
    """Retrieves an article by date and title."""
    try:
        entrydate = datetime.date(year, month, day)
    except:
        abort(401)

    print "Title: %s; Date: %s" % (title, entrydate)

    entry = query_db(
            'SELECT * FROM entry \
             WHERE slug = ? \
             AND creation_date = ?',
             [title, entrydate],
             one=True)

    if entry is None:
        abort(401)

    else:
        return render_template('entry.html', entry=entry)

if __name__ == "__main__":
    app.run()

# -*- coding: utf-8 -*-
"""

    blog.views
    ~~~~~~~~~~~~~~~~~~

    This module handles views by using
    flask's app.route() decorator.

    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

from blog import app
from flask import Flask, request, session, g, redirect, \
     render_template, abort, flash, url_for
from helpers import check_password_hash, slugify_entry, \
     fill_entries, entry_pages, unpack_pages, split_pages
from lib import factory
import datetime

# Loading the Data Abstract Layer object
try:
    data_layer = factory(app.config['PLATFORM'])
except NameError as e:
    print e


@app.before_request
def before_request():
    """
    Connects to the database before each request and
    looks up the current user.
    """
    g.db = data_layer.connect_db()
    g.user = None 
    
    if 'user_id' in session:
        g.user = data_layer.load_user_profile(session['user_id'])


@app.after_request
def after_request(response):
    """Closes the database again at the end of the request."""
    data_layer.close()
    return response


@app.route('/')
@app.route('/tags/<tagname>')
def list_entries(tagname=None):
    """
    Returns a list of entries in the form of pages containing
    MAX_PAGE_ENTRIES entries;
    the default page argument, being ``1'', refers to the latest
    MAX_PAGE_ENTRIES entries.

    Optionally, this method accepts a tagname for tag filtering.
    """
    try:
        page = int(request.args['page'])
        if page <= 0:
            page = 1
    except:
        page = 1

    # Calculate the right offset
    offset = app.config['MAX_PAGE_ENTRIES']*(page-1)
    
    # Obtain entries and num_entries
    entries, num_entries = data_layer.num_entries(tagname, offset)

    # This happens when trying to access a non-existent page
    if len(entries) == 0 and page !=1: 
        abort(404)

    # Splitting pages
    splitted_pages = unpack_pages(split_pages(page, entry_pages(num_entries)))

    # Jinja2 render
    return render_template("list_entries.html", actual_page=page, entries=entries, pages=splitted_pages)


@app.route('/articles/<int:year>/<int:month>/<int:day>/<title>')
def view_entry(year, month, day, title):
    """Retrieves an article by date and title."""
    try:
        entrydate = datetime.date(year, month, day)
    except:
        abort(400)

    entry = data_layer.query_db(
    """
    SELECT * FROM Entry
    WHERE slug = ?
    AND creation_date = ?
    """,
    [title, entrydate], one=True)

    if entry is None:
        abort(404)
    else:
        fill_entries([entry])
        return render_template('list_entries.html', entries=[entry])


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user into the application given his credentials."""
    error = None
    if request.method == 'POST':
        user = data_layer.get_user(request.form['username'])

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
        errors = []
        if request.method == 'POST':

            if request.form['title'] == '':
                errors.append('No title supplied')

            if request.form['entry_text'] == '':
                errors.append('Message body is empty')

            if (errors == []):
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
                lastid = data_layer.query_db('SELECT last_insert_rowid()',one=True)['last_insert_rowid()']
                if request.form['tags'] !='':
                    process_tags(lastid, request.form['tags'].split())

                flash('Entry added.')
                return redirect(url_for('list_entries'))

        return render_template('add_entry.html', errors=errors)

    return redirect(url_for('list_entries'))


@app.route('/admin')
def admin_panel():
    """Display a panel for administration purposes."""
    if g.user is not None:
        if g.user['role_name'] == 'administrator':
            entries_list = data_layer.query_db(
                           """
                           SELECT id, user_id_FK, slug, title 
                           FROM entry
                           """)
            fill_tags(entries_list)
            fill_author(entries_list)

            return render_template('admin.html', entries=entries_list)

        else:
            return redirect(url_for('list_entries'))
    else:
        return redirect(url_for('login'))


if __name__ == "__main__":
    app.run()

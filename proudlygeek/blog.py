# -*- coding: utf-8 -*-
"""

    ProudlyGeek's Blog
    ~~~~~~~~~~~~~~~~~~

    A simple blog app written with Flask and sqlite3.

    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""
from flask import Flask, request, session, g, url_for, redirect, \
     render_template, abort, flash, Markup
from contextlib import closing

import sqlite3
import math
import hashlib
import datetime
import re
import markdown
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
        DATABASE = 'blog.db'

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

def process_tags(entry_id, tags_list):
    """
    For each tag into tags_list it retrieves it's id from the database;
    if a supplied tag is not recorded then it creates a new database record.
    """
    for tag in tags_list:
        current=query_db('SELECT id FROM tag \
                          WHERE tag.name = ?',
                          [tag],
                          one=True)

        if current is None:
            g.db.execute('INSERT INTO tag \
                          VALUES (null, ?)',
                          [tag])

            current = query_db('SELECT last_insert_rowid()', 
                                one=True)['last_insert_rowid()']
        else:
            current = current['id']

        g.db.execute('INSERT INTO entry_tags \
                      VALUES (?, ?)',
                      (entry_id, current))
    g.db.commit()


def fill_tags(entries):
    """
    Convenience function which retrieves all the tags and 
    inserts them in the right entry dictionary. 
    This is useful for templating purposes (i.e. displaying
    all entry's tags near the title of the entry).
    """
    for entry in entries:
        rs = g.db.execute(
             'SELECT tag.name FROM tag \
              JOIN entry_tags ON tag.id = entry_tags.id_tag_FK \
              WHERE entry_tags.id_entry_FK = ?',
              [entry['id']])
        entry['tags'] = [item[0] for item in rs.fetchall()]

def fill_author(entries):
    """
    Convenience function which inserts the author's name into
    the dictionary structure passed by default.
    This is useful for templating purpose.
    """
    for entry in entries:
        rs = g.db.execute(
             """
             SELECT user.username 
             FROM user
             WHERE user.id = ?
             """,
             [entry['user_id_FK']])
        entry['author'] = rs.fetchall()[0][0]

def fill_humanized_dates(entries):
    """
    Convenience function which inserts a humanized date
    into the passed entries dictionary.
    """
    for entry in entries:
        entry['human_date'] = humanize_date(entry['creation_date'])

def generate_readmore(entry, single=False):
    """
    Replaces any <hr /> tag with an URL to the full entry's text
    and strips down the current entry's text to make a summary.
    """
    year, month, day = entry['creation_date'].split('-')
    entry_url = """<a class="readmore" href="%s"> Read more about "%s"...</a>""" \
                 % (url_for('view_entry', year=year, month=month, day=day, 
                 title=entry['slug']), entry['title'])

    strip_index = entry['content'].find("""<hr />""")
    
    # Stripping down text and appending the generated URL
    if strip_index > 0:
        if single:
            entry['content'] = entry['content'][:strip_index] + Markup("""<br />""") + entry['content'][strip_index+6:]
        else:
            entry['content'] = entry['content'][:strip_index] + Markup(entry_url)

    # Add a separator at the end of the post
    entry['content'] = entry['content'] + Markup("""<hr />""")

def fill_markdown_content(entries):
    """
    Convenience function which converts entry's body Markdown
    syntax to HTML code.
    """
    if len(entries) == 1:
        single = True
    else:
        single = False

    for entry in entries:
        entry['content'] = Markup(markdown.markdown(entry['body']))
        generate_readmore(entry, single)



def humanize_date(date_string):
    """
    Converts numerics date to a more friendly form;
    given a numeric date formatted as "<Year>-<Month>-<Day>""
    it returns the string "<Month Name> <Day>".
    """
    date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
    return date.strftime('%d %b').upper()


def fill_entries(entries):
    """
    Convenience function which inserts several new fields
    into the entries dict (see above).
    """
    # Add humanized post date
    fill_humanized_dates(entries)
    # Add tags
    fill_tags(entries)
    # Add Markdown entry
    fill_markdown_content(entries)
    # Add author
    #fill_author(entries)


def entry_pages():
    """
    Returns the minimum amount of pages needed for displaying
    a certain amount of entries (defined into the config var
    MAX_PAGE_ENTRIES).

    The used formula is:
              __                     __
             |     # Total Entries     |
        CEIL |   -------------------   |
             |   # MAX_PAGE_ENTRIES    |
    """
    total_entries = query_db(
                    """
                    SELECT COUNT(*)
                    FROM entry
                    """,
                    one=True)['COUNT(*)']

    max_page_entries = app.config['MAX_PAGE_ENTRIES']*1.0

    try:
        entry_pages = int(math.ceil(total_entries/max_page_entries))
    except ZeroDivisionError as Err:
        print "Critical Error (Is MAX_PAGE_ENTRIES zero?): %s" % (Err)

    # If the result is zero then set default to one page
    if entry_pages == 0:
        entry_pages = 1

    return entry_pages


def split_pages(currentpage, totalpages):
    """
    Splits a certain number of pages into several
    lists; for example, if the current page is 31 on a total of 115
    pages the return tuple is: 
    
    ([1, 2, 3, 4], [27, 28, 29, 30, 31, 32, 33, 34], [112, 113, 114, 115])
    """
    # Check if currentpage is less than the total
    if currentpage > totalpages:
        raise NameError('The actual page value {0} is more than {1}.'.format(currentpage, totalpages))

    # Creates an ordered list of *totalpages* dimension
    pag = [number+1 for number in range(totalpages)]

    # If the total size is less than 18 then there's no need to split
    if len(pag) < 18:
        return pag
    else:
        if (currentpage in pag[:10]):
            return (pag[:currentpage+3], pag[len(pag)-4:])
        elif (currentpage in pag[len(pag)-9:]):
            return pag[:4], pag[currentpage-5:]
        else:
            return pag[:4],pag[currentpage-5:currentpage+3], pag[len(pag)-4:]


def unpack_pages(pages):
    """
    Turns a tuple of several lists obtained from the split_pages function
    (see above) into a plain list;

    for example, the following tuple:

    ([1, 2, 3, 4], [27, 28, 29, 30, 31, 32, 33, 34], [112, 113, 114, 115])

    returns the list:

    [1, 2, 3, 4, '...', 27, 28, 29, 30, 31, 32, 33, 34, '...', 112, 113, 114, 115]
    """
    # Duck Typing: If it is a plain tuple there's no need to unpack
    try:
        pages[0][0]
    except TypeError:
        return pages

    plainlist = []
    for page in pages:
        for item in page:
            plainlist.append(item)
        if item != pages[-1][-1]: plainlist.append("...")
    return plainlist


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
                 """
                 SELECT user.id, rank.role_name
                 FROM user, rank 
                 WHERE user.rank_id_FK = rank.id
                 AND user.id = ?
                 """, 
                 [session['user_id']], 
                 one=True)


@app.after_request
def after_request(response):
    """Closes the database again at the end of the request."""
    g.db.close()
    return response


@app.route('/')
def list_entries():
    """
    Returns a list of entries in the form of pages containing
    MAX_PAGE_ENTRIES entries;
    the default page argument, being ``1'', refers to the latest
    MAX_PAGE_ENTRIES entries.
    """
    try:
        page = int(request.args['page'])
        if page <= 0:
            page = 1
    except:
        page = 1

    # Calculate the right offset
    offset = app.config['MAX_PAGE_ENTRIES']*(page-1)
    entries = query_db(
              """
              SELECT id, slug, title, body, last_date, 
                     creation_date, user_id_FK
              FROM entry
              ORDER BY creation_date DESC, id DESC 
              LIMIT %d OFFSET %d
              """ % (app.config['MAX_PAGE_ENTRIES'], offset))
    # This happens when trying to access a non-existent page
    if len(entries) == 0 and page !=1:
        abort(404)
    # Filling entries
    fill_entries(entries)

    # Splitting pages
    splitted_pages = unpack_pages(split_pages(page, entry_pages()))

    # Jinja2 render
    return render_template("list_entries.html", actual_page=page, entries=entries, pages=splitted_pages)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user into the application given his credentials."""
    error = None
    if request.method == 'POST':
        user = query_db(
               """
               SELECT * FROM user
               WHERE username = ?
               """, 
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
                lastid = query_db('SELECT last_insert_rowid()',one=True)['last_insert_rowid()']
                if request.form['tags'] !='':
                    process_tags(lastid, request.form['tags'].split())

                flash('Entry added.')
                return redirect(url_for('list_entries'))

        return render_template('add_entry.html', errors=errors)

    return redirect(url_for('list_entries'))


@app.route('/articles/<int:year>/<int:month>/<int:day>/<title>')
def view_entry(year, month, day, title):
    """Retrieves an article by date and title."""
    try:
        entrydate = datetime.date(year, month, day)
    except:
        abort(400)

    entry = query_db(
            'SELECT * FROM entry \
             WHERE slug = ? \
             AND creation_date = ?',
             [title, entrydate],
             one=True)

    if entry is None:
        abort(404)
    else:
        fill_entries([entry])
        return render_template('list_entries.html', entries=[entry])


@app.route('/tags/<tagname>')
def list_entries_by_tag(tagname):
    """Lists all entries given a tag's name."""
    entries = query_db(
              """
              SELECT entry.id, entry.slug, entry.title, entry.body, 
              entry.last_date,entry.creation_date FROM entry
              JOIN entry_tags ON entry.id = entry_tags.id_entry_FK
              JOIN tag ON entry_tags.id_tag_FK = tag.id
              WHERE tag.name = ?
              ORDER BY entry.creation_date DESC, entry.id DESC
              """,
              [tagname])
    fill_entries(entries)
    return render_template("list_entries.html", entries=entries)


@app.route('/admin')
def admin_panel():
    """Display a panel for administration purposes."""
    if g.user is not None:
        if g.user['role_name'] == 'administrator':
            entries_list = query_db(
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

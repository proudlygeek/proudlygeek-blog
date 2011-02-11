# -*- coding: utf-8 -*-
"""

    blog.db
    ~~~~~~~~~~~~~~~~~~

    Experimental library to implement a data layer for
    Proudlygeek's blog app. It currently supports sqlite
    and Google App Engine's Datastore.


    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

from views import app
from flask import g, Markup
from contextlib import closing
from blog.helpers import slugify_entry, filter_projects


if app.config['PLATFORM']=='sqlite':
    try:
        import sqlite3
        import datetime
        from blog.helpers import fill_entries
    except ImportError:
        print "Database Wrapper error (sqlite)."

if app.config['PLATFORM']=='gae':
    try:
        from google.appengine.ext import db
        from blog.models import User, Entry
        from blog.helpers import fill_markdown_content, \
             generate_readmore

    except ImportError:
        print "Database Wrapper error (GAE)."


class DataLayer(object):
    def __init__(self):
        pass


class SQLiteLayer(DataLayer):
    def __init__(self):
        super(SQLiteLayer, self).__init__()

    def connect_db(self):
        """Returns a new connection to the database."""
        return sqlite3.connect(app.config['DATABASE'])

    def init_db(self, testdb=False):
        """Creates the database tables."""
#        if not testdb:
#            schema = 'schema.sql'
#        else:
#            schema = 'fixture-sqlite.sql'
#            DATABASE = 'blog.db'
#
#        with closing(self.connect_db()) as db:
#            with app.open_resource(schema) as f:
#                db.cursor().executescript(f.read())
#            db.commit()
        pass
    
    def close(self):
        """Closes the database connection at the end of the request."""
        g.db.close()

    def query_db(self, query, args=(), one=False):
        """Queries the database and returns a list of dictionaries."""
        cur = g.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv
    
    def get_entries(self, tagname, offset):
        """
        Retrieves entries from the database. 
        It returns a tuple following the scheme:

        (entries_list, #entries)

        Where entries_list is a list of entries for the given tagname
        (which can be None) and #entries is their total number.
        """
        if not tagname:
            entries = self.query_db(
                      """
                      SELECT *
                      FROM Entry
                      ORDER BY creation_date DESC, id DESC 
                      LIMIT ? OFFSET ? 
                      """, 
                      (app.config['MAX_PAGE_ENTRIES'], offset))

            num_entries = self.query_db(
                          """
                          SELECT COUNT(*)
                          FROM Entry
                          """,
                          one=True)['COUNT(*)']

        else:
            entries = self.query_db(
                      """
                      SELECT entry.id, entry.slug, entry.title, entry.body, 
                      entry.last_date,entry.creation_date FROM entry
                      JOIN entry_tags ON entry.id = entry_tags.id_entry_FK
                      JOIN tag ON entry_tags.id_tag_FK = tag.id
                      WHERE tag.name = ?
                      ORDER BY entry.creation_date DESC, entry.id DESC
                      """,
                      [tagname])

            num_entries = self.query_db(
                    """
                    SELECT COUNT(*)
                    FROM entry
                    JOIN entry_tags ON entry.id = entry_tags.id_entry_FK
                    JOIN tag on entry_tags.id_tag_FK = tag.id
                    WHERE tag.name = ?
                    """,
                    [tagname], one=True)['COUNT(*)']
        
        # Filling entries (Join tables for sqlite)
        fill_entries(entries)
        # Return the entries 
        return entries, num_entries

    def get_entry(self, title, entry_date):
        """
        Retrieves a specific entry by specifing a creation date
        and a title; this method is expecting to 
        fetch one or none entries from the database.
        """
        entry = self.query_db(
        """
        SELECT * FROM Entry
        WHERE slug = ?
        AND creation_date = ?
        """,
        [title, entry_date], one=True)

        if entry:
            fill_entries([entry])
            return entry

    
    def get_recent_entries(self, n):
        """
        Retrieves the latest n entries sorted by descending date
        order; this is expecially useful for RSS feeds generation.
        """
        entries = self.query_db(
                              """
                              SELECT *
                              FROM Entry
                              ORDER BY creation_date DESC, id DESC 
                              LIMIT ? 
                              """, 
                              n)

        # Filling entries (Join tables for sqlite)
        fill_entries(entries)
        return entries


    def get_user(self, username):
        """Return the user model if the given username exists."""
        if username:
            user = self.query_db(
                   """
                   SELECT * FROM User
                   WHERE username = ?
                   """, 
                   [username], one=True)
        else:
            user = None

        return user

    def load_user_profile(self, id):
        """Load a user's profile given his unique id."""
        user_profile = self.query_db(
                 """
                 SELECT user.id, rank.role_name
                 FROM user, rank 
                 WHERE user.rank_id_FK = rank.id
                 AND user.id = ?
                 """, 
                 [id], 
                 one=True)

        return user_profile

    def insert_entry(self, title, text, owner, tags):
        """Inserts a new entry post into the database."""
        today = datetime.date.today()
        creation_date = today.strftime('%Y-%m-%d')
        last_date = creation_date

        g.db.execute(
        """
        INSERT INTO entry
        VALUES (null, ?, ?, ?, ?, ?, ?)
        """,
        (slugify_entry(title),
         title,
         text,
         creation_date,
         last_date,
         g.user['id']))

        g.db.commit()
        lastid = self.query_db('SELECT last_insert_rowid()',one=True)['last_insert_rowid()']
        if tags !='':
           self.process_tags(lastid, tags.split())

    def process_tags(self, entry_id, tags_list):
        """
        For each tag into tags_list it retrieves it's id from the database;
        if a supplied tag is not recorded then it creates a new database record.
        """
        for tag in tags_list:
            current=self.query_db('SELECT id FROM tag \
                              WHERE tag.name = ?',
                              [tag],
                              one=True)

            if current is None:
                g.db.execute('INSERT INTO tag \
                              VALUES (null, ?)',
                              [tag])

                current = self.query_db('SELECT last_insert_rowid()', 
                                    one=True)['last_insert_rowid()']
            else:
                current = current['id']

            g.db.execute('INSERT INTO entry_tags \
                          VALUES (?, ?)',
                          (entry_id, current))
        g.db.commit()


class BigtableLayer(DataLayer):
    def __init__(self):
        # Create sample user admin:ciao
        #user = User(username="Proudlygeek",key_name="admin_key",
        #       password="b133a0c0e9bee3be20163d2ad31d6248db292aa6dcb1ee087a2aa50e0fc75ae2",
        #       rank='admin')
        # Saves result to datastore
        #db.put([user])
        pass

    def connect_db(self):
        pass
    
    def close(self):
        pass
    
    def query_db(self, query, args=(), one=False):
        """
        Queries the Datastore by using GQL syntax.
        """
        # Parse question marks
        parsed_query = replace_questionmarks(query, args)
        # Run GQL Query
        rs = db.GqlQuery(parsed_query)
        return rs
    
    def get_entries(self, tagname, offset):
        """
        Retrieves entries from the datastore. 
        It returns a tuple following the scheme:

        (entries_list, #entries)

        Where entries_list is a list of entries for the given tagname
        (which can be None) and #entries is their total number.
        """
        if not tagname:
            entries = self.query_db(
            """
            SELECT *
            FROM Entry
            ORDER BY last_date DESC
            LIMIT ? OFFSET ?
            """,
            (app.config['MAX_PAGE_ENTRIES'], offset))
            
            num_entries = db.GqlQuery(
            """
            SELECT *
            FROM Entry
            """).count()

        else:
            entries = self.query_db(
            """
            SELECT *
            FROM Entry
            WHERE tags = '?'
            ORDER BY last_date DESC
            LIMIT ? OFFSET ?
            """,
            (tagname, app.config['MAX_PAGE_ENTRIES'], offset ))
            
            num_entries = db.GqlQuery(
            """
            SELECT *
            FROM Entry
            WHERE tags = '?'
            """).count()
        
        # Parse Markdown Text
        list_entries = gqlentries_to_list(entries)
        
        # Filter Projects
        if not tagname: filter_projects(list_entries)

        fill_markdown_content(list_entries)
        
        return list_entries, num_entries

    def get_entry(self, title, entry_date):
        """
        Retrieves a specific entry by specifing a creation date
        and a title; this method is expecting to 
        fetch one or none entries from the database.
        """
        entry = db.GqlQuery(
        """
        SELECT * FROM Entry
        WHERE slug =:1
        AND creation_only_date =:2
        """, title, entry_date).get()

        list_entry = gqlentries_to_list([entry])
        fill_markdown_content(list_entry)

        return list_entry[0]

    def get_entry_by_id(self, entry_id):
        """
        Retrieves a specific entry by specifing an unique
        ID as argument; this method is expectin to fetch
        one or none entries from the database.
        """
        k = db.Key.from_path('Entry', entry_id)
        entry = db.get(k)

        list_entry = gqlentries_to_list([entry])
        return list_entry[0]


    def get_recent_entries(self, n):
        """
        Retrieves the latest n entries sorted by descending date
        order; this is expecially useful for RSS feeds generation.
        """
        entries = db.GqlQuery(
        """
        SELECT *
        FROM Entry
        ORDER BY last_date DESC
        """).fetch(n)
         
        # Parse Markdown Text
        list_entries = gqlentries_to_list(entries)
        
        # Filter Projects
        filter_projects(list_entries)

        fill_markdown_content(list_entries)

        return list_entries


    def get_user(self, username):
        """Return the user model if the given username exists."""
        user = db.GqlQuery(
        """
        SELECT * 
        FROM User
        WHERE username = :1
        """, username).get()

        return gqluser_to_dict(user)


    def load_user_profile(self, id_or_name):
        """Load a user's profile given his unique id."""
        profile_key = db.Key.from_path('User', str(id_or_name))
        user_profile = db.get(profile_key)

        return gqluser_to_dict(user_profile)


    def insert_entry(self, title, text, owner, tags):
        """Insert a new entry."""
        # Retrieves Owner's key
        owner_key = db.Key.from_path('User', owner)
        # Create a new entity (without tags)
        new_entry = Entry(
                    slug=slugify_entry(title),
                    title=title,
                    body=text,
                    user_id_FK=owner_key)

        # Insert tags into entry's list
        for tag in list(tags.split()):
            new_entry.tags.append(tag)

        # Store Entity
        db.put(new_entry)


    def update_entry(self, entry_id, title, text, tags):
        """Update an existing entry."""
        # Retrieve old entity
        entry_key = db.Key.from_path('Entry', entry_id)
        existing_entry = db.get(entry_key)

        # Update entity
        existing_entry.slug = slugify_entry(title)
        existing_entry.title = title
        existing_entry.body = text
        # Insert tags into entry's list
        existing_entry.tags = tags.split()
        # Store Entity
        existing_entry.put()

def factory(db_name):
    """
    Returns the appropriate data layer class by using the db_name
    parameter as a dictionary key; Right now, it contains entries for
    sqlite and gae.
    """
    supported_db={'sqlite': SQLiteLayer, 'gae':BigtableLayer}
    return supported_db[db_name]()


def replace_questionmarks(string, args=()):
    """
    Replaces all question marks in a string with the sequential argument
    contained into args().

    For example, the query;

    SELECT * FROM User
    WHERE User.name = ? AND
    User.pass = ?

    with args = ('Tom','test')
    
    become

    SELECT * from User
    WHERE User.name = 'Tom' AND
    User.pass = 'test'

    This is useful for traslating SQL SELECT statements into GQL Queries.
    """
    # Convert tuple to list and reverts it (for argument pop)
    args = list(args)[::-1]
    newstring = ""
    for char in string:
        if char == '?':
            char = str(args.pop())
        newstring+=char
    return newstring


def gqlentries_to_list(gql_rs):
    """
    Returns a list of entries given a gql resultset with the following
    structure:

    [{<rs1>},{<rs2>},...,{<rsi>},{<rsi+1>},...,{<rsn>}] for 1<=i<=n
     
    where the generic dictionary element {<rsi>} is:
    
    {'entry_id':entry_id_i,
     'slug':slug_i,
     'author':user_id_FK_i.username,
     'title':title_i, 
     'body':body_i, 
     'creation_date':creation_date_i,
     'creation_only_date':creation_only_date_i,
     'human_date':human_date_i,
     'last_date':last_date_i,
     'user_id_FK':user_id_FK,
     'tags':[<tag1>,<tag2>,...,<tagj>,<tagj+1>,...,<tagm>] for 1<=j<=m
    }
    """
    result_list = list()
    for item in gql_rs:
        d = {
        'entry_id':item.key().id(),
        'slug':item.slug,
        'author':item.user_id_FK.username,
        'title':item.title,
        'body':item.body,
        'creation_date':item.creation_date,
        'creation_only_date':item.creation_only_date,
        'human_date':item.creation_date.strftime('%d %b').upper(),
        'last_date':item.last_date,
        'user_id_FK':item.user_id_FK,
        'tags':item.tags}
        result_list.append(d)
    
    return result_list


def gqluser_to_dict(gql_user):
    """
    Converts a single user gql resultset using the following dict structure:

    {'id':id_or_keyname,
     'username':username, 
     'password':hashed_password, 
     'rank':user_rank
    }
    """
    if not gql_user:
        return None

    d = {'id':gql_user.key().id_or_name(),
         'username':gql_user.username,
         'password':gql_user.password,
         'rank':gql_user.rank}

    return d

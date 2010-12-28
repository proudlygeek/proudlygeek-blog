# -*- coding: utf-8 -*-
"""

    lib.dal.db
    ~~~~~~~~~~~~~~~~~~

    Experimental library to implement a data layer for
    Proudlygeek's blog app. It currently supports sqlite
    and, in the near future, Google App Engine's Datastore.


    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

from blog import app
from flask import g
from contextlib import closing


if app.config['PLATFORM']=='sqlite':
    try:
        import sqlite3
        from blog.helpers import fill_entries
    except NameError as e:
        print e

if app.config['PLATFORM']=='gae':
    try:
        from google.appengine.ext import db
        from blog.models import Rank, User, Entry


    except NameError as e:
        print e


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
        if not testdb:
            schema = 'schema.sql'
        else:
            schema = 'test_db.sql'
            DATABASE = 'blog.db'

        with closing(self.connect_db()) as db:
            with app.open_resource(schema) as f:
                db.cursor().executescript(f.read())
            db.commit()
    
    def close(self):
        """Closes the database connection at the end of the request."""
        g.db.close()

    def query_db(self, query, args=(), one=False):
        """Queries the database and returns a list of dictionaries."""
        cur = g.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv
    
    def num_entries(self, tagname, offset):
        """Returns the number of entries of a table."""
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
        

class BigtableLayer(DataLayer):
    def __init__(self):
        # Create sample user
        rank = Rank(role_name="admin",key_name="role_key")
        user = User(username="bargio",key_name="bargio_key",
               password = "13033eddc3fdeecc0ed03bdc019c25890ba906658addad9fefe",
               rank_id_fk = rank)
        entry = Entry(key_name="entry_key",
                slug="hello-world",
                title="""Hello World!""",
                body="""Lorem ipsum mania!""",
                user_id_FK=user,
                tags=['tag1','tag2','tag3'])
        # Saves result to datastore
        db.put([rank, user, entry])

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
        return gql_to_list(rs)
    
    def num_entries(self, tagname, offset):
        """Returns the number of entries of a table."""
        if not tagname:
            entries = self.query_db(
            """
            SELECT *
            FROM Entry
            ORDER BY creation_date DESC
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
            ORDER BY creation_date DESC
            LIMIT ? OFFSET ?
            """,
            (tagname, app.config['MAX_PAGE_ENTRIES'], offset ))
            
            num_entries = db.GqlQuery(
            """
            SELECT *
            FROM Entry
            WHERE tags = '?'
            """).count()
        
        return entries, num_entries
         
        
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


def gql_to_list(gql_rs):
    """
    Returns a list of entries given a gql resultset with the following
    structure:

    [{<rs1>},{<rs2>},...,{<rsi>},{<rsi+1>},...,{<rsn>}] for 1<=i<=n
     
    where the generic dictionary element {<rsi>} is:
    
    {'slug':slug_i, 
     'title':title_i, 
     'body':body_i, 
     'creation_date':creation_date_i,
     'human_date':human_date_i,
     'last_date':last_date_i,
     'user_id_FK':user_id_FK,
     'tags':[<tag1>,<tag2>,...,<tagj>,<tagj+1>,...,<tagm>] for 1<=j<=m
    }
    """
    result_list = list()
    for item in gql_rs:
        d = {'slug':item.slug,
        'title':item.title,
        'body':item.body,
        'creation_date':item.creation_date.strftime('%Y-%m-%d'),
        'human_date':item.creation_date.strftime('%d %b').upper(),
        'last_date':item.last_date.strftime('%Y-%m-%d'),
        'user_id_FK':item.user_id_FK,
        'tags':item.tags}
        result_list.append(d)
    
    return result_list

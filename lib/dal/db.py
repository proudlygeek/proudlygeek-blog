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

    def query_db(self, query, args=(), one=False):
        """Queries the database and returns a list of dictionaries."""
        cur = g.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv


class BigtableLayer(DataLayer):
    def __init__(self):
        pass

def factory(db_name):
    supported_db={'sqlite': SQLiteLayer, 'gae':BigtableLayer}
    return supported_db[db_name]()

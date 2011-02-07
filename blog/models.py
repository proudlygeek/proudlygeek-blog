# -*- coding: utf-8 -*-
"""

    blog.helpers
    ~~~~~~~~~~~~~~~~~~

    This module contains helper functions mainly used by 
    the views module.

    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

from google.appengine.ext import db


class User(db.Model):
    """
    This class models a user into a
    Google App Engine's Datastore entity.
    """
    username = db.StringProperty(required=True)
    password = db.StringProperty(required=True, indexed=False)
    rank = db.StringProperty(required=True, 
            choices = ['user','admin'],
            default = 'user')


class Entry(db.Model):
    """
    This class models a blog post into a
    Google App Engine's Datastore entity.
    """
    slug = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    body = db.TextProperty(required=True)
    creation_date = db.DateTimeProperty(auto_now_add=True)
    last_date = db.DateTimeProperty(auto_now=True)
    user_id_FK = db.ReferenceProperty(User, collection_name='Owner')
    tags = db.StringListProperty()

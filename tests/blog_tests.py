# -*:- coding: utf-8 -*-
"""

    Blog Tests
    ~~~~~~~~~~

    Tests the blog application.

    :copyright: © 2010 by Gianluca Bargelli.
    :license: MIT, see LICENSE for more details.


"""

from flask import Flask
import os
import math
import unittest
import tempfile
import datetime
from blog import app, data_layer
from blog import views
from blog import helpers


class BlogTestCase(unittest.TestCase):
    

    def setUp(self):
        """Before each test, set up a sample database"""
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        self.app = app.test_client()
        data_layer.init_db(testdb=True)

    def tearDown(self):
        """Get rid of the database again after each test."""
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    # Helper Functions
    def login(self, username, password):
        """Helper function for user login."""
        return self.app.post('/login', data={'username': username,
                                             'password': password},
                                             follow_redirects=True)

    def logout(self):
        """Helper function for user logout."""
        return self.app.get('/logout', follow_redirects=True)

    def add_entry(self, title, text, tags=""):
        """Helper function for adding entries."""
        rv = self.app.post('/add_entry', data={'title': title,
                                               'entry_text': text,
                                               'tags': tags},
                                               follow_redirects=True)
        if title and text:
            assert 'Entry added.' in rv.data

        return rv

    def view_entry(self, year, month, day, slug):
        """Helper function for viewing single entries."""
        return self.app.get('/articles/%s/%s/%s/%s' % (year,
                                                       month,
                                                       day,
                                                       slug))
    def create_sample_entries(self, n=10):
        """Simply calls add_entry *n* times."""
        for entry in range(n):
            self.add_entry('Test Title', 'this is a test!','tag1 tag2 tag3')

    def test_empty_db(self):
        """Tests if an initial database is empty."""
        rv = self.app.get("/")
        assert 'No entries here so far' in rv.data

    def test_login_logout(self):
        """Tests if login and logout works correctly."""
        # Testing GOOD username, GOOD password
        rv = self.login('test', 'test')
        assert 'You were logged in' in rv.data
        # Testing logout after a successful login
        rv = self.logout()
        assert 'You were logged out' in rv.data
        # Testing GOOD username, BAD password
        rv = self.login('test', 'rest')
        assert 'Invalid password' in rv.data
        # Testing BAD username, BAD password
        rv = self.login('pest', 'rest')
        assert 'Invalid username' in rv.data
        # Testing logout without a login
        rv = self.logout()
        assert """<p><a href = "/login">Login</a></p>""" \
        in rv.data

    def test_add_entry(self):
        """Add a test entry and see if it works correctly."""
        today = datetime.date.today()
        self.login('test', 'test')
        rv = self.app.get("/add_entry")
        assert "Enter your message:" in rv.data
        rv = self.add_entry('Test Title', 'this is a test!')
        # Testing the correctness of the inserted data
        assert """<p>%s</p>""" % (today.strftime('%d %b').upper()) in rv.data
        assert """<a href = /articles/%s/%s/%s/%s>Test Title</a>""" \
               % (today.year, today.month, today.day, 'this-is-a-test')
        assert """<p>this is a test!</p>""" in rv.data
        # Testing BLANK Title
        rv = self.add_entry('','this is a test!')
        assert 'No title supplied' in rv.data
        # Testing BLANK Text
        rv = self.add_entry('Test Title','')
        assert 'Message body is empty' in rv.data
        # Testing BLANK Title, BLANK Text
        rv = self.add_entry('','')
        assert 'No title supplied' in rv.data
        assert 'Message body is empty' in rv.data


    def test_slugify_entry(self):
        """Test if slugify_entry generates a correct slug."""
        # Basic check
        rv = helpers.slugify_entry(u"""!!"£$%&/()=?^'[]@#`<>'"%ciao mondo!""")
        assert u'ciao-mondo' == rv

    def test_add_entry_with_tags(self):
        """Add a test entry with multiple tags."""
        self.login('test','test')
        self.app.get('/add_entry')
        rv = self.add_entry('Test Title', 'this is a test!', 'tag1 tag2 tag3')
        assert 'tag1' in rv.data
        assert 'tag2' in rv.data
        assert 'tag3' in rv.data

    def test_view_entry(self):
        """Tests if entry view works correctly."""
        today = datetime.date.today()
        # Login
        self.login('test', 'test')
        # Adding an entry
        self.add_entry('Test Title', 'this is a test!','tag1 tag2 tag3')
        # Testing GOOD date, GOOD slug
        rv = self.view_entry(today.year, today.month, today.day, 'test-title')
        assert '404 Not Found' not in rv.data
        assert '400 Bad Request' not in rv.data
        assert 'tag1' in rv.data
        assert 'tag2' in rv.data
        assert 'tag3' in rv.data
        # Testing GOOD date, BAD slug
        rv = self.view_entry(today.year, today.month, today.day, 'test123')
        assert '404 Not Found' in rv.data
        # Testing BAD date, GOOD slug
        rv = self.view_entry('1800','01','01','test-title')
        assert '404 Not Found' in rv.data
        # Testing WRONG date
        rv = self.view_entry('9999999','13','40','test-title')
        assert '400 Bad Request' in rv.data

    def test_admin_panel(self):
        """Tests if access is granted correctly to the admin panel."""
        # Access with no login
        rv = self.app.get('/admin', follow_redirects=True)
        assert 'Please login' in rv.data
        # Login with administrator
        self.login('test', 'test')
        rv = self.app.get('/admin')
        assert 'Administration Panel' in rv.data
        # Logout
        self.logout()
        # Login with normal user
        self.login('user', 'test')
        rv = self.app.get('/admin')
        assert 'Administration Panel' not in rv.data

    def test_pagination(self):
        """
        Tests if the pagination algorithms works correctly.
        This test is extremely SLOW.
        """
        # Login
        self.login('test','test')
        # Create 27 entries
        self.create_sample_entries(27)
        # Check if page numbers are correct
        entry_pages_check = int(math.ceil(27/app.config['MAX_PAGE_ENTRIES']*1.0))
        rv = self.app.get('/')
        print rv.data
        print entry_pages_check
        assert str(entry_pages_check) in rv.data

    def test_get_page(self):
        """
        Tests various combinations of the '?page=' GET parameter
        normally used in the the list_entries methods.
        """
        # Login
        self.login('test','test')
        # Create sample entries
        self.create_sample_entries(10)
        # GET test #1: Request existing page
        rv = self.app.get('/?page=2', follow_redirects=True)
        assert "pagination" in rv.data
        # GET test #2: Request negative page
        rv = self.app.get('/?page=-1', follow_redirects=True)
        assert "pagination" in rv.data
        # GET test #3: Request non-existing page
        rv = self.app.get('/?page=3', follow_redirects=True)
        print rv.data
        assert "404 Not Found" in rv.data

    def test_split_unpack(self):                                              
        """
        Tests if pagination splitting/unpacking is working correctly          
        using every time a different number of entries.
        This test assumes that MAX_PAGES_ENTRIES = 5 (See config)
        """
        # Login
        self.login('test','test')
        # Create eight entries                      
        self.create_sample_entries(8)
        # It is expecting two pages like this -> ‹‹ previous 1 2 next ›› 
        rv = self.app.get('/')
        assert """<div class = "pagination">\n  \n    """ in rv.data
        assert """<span>\xe2\x80\xb9\xe2\x80\xb9 previous</span>\n  \n  \n    \n      """ in rv.data
        assert """<span>1</span>\n    \n  \n    \n      """ in rv.data
        assert """<a href="/?page=2">2</a>\n    \n  \n  \n    """ in rv.data
        assert """<a href="/?page=2">next \xe2\x80\xba\xe2\x80\xba</a>\n  </div>""" in rv.data
        # Add eighty-two more entries to trigger pagination split functions -> (82+8)/5 = 18
        self.create_sample_entries(82)
        # Expecting this pagination -> ‹‹ previous 1 2 3 4 ... 15 16 17 18 next ››
        rv = self.app.get('/')
        print rv.data
        assert """<div class = "pagination">\n  \n    """ in rv.data
        assert """<span>\xe2\x80\xb9\xe2\x80\xb9 previous</span>\n  \n  \n    \n""" in rv.data
        assert """<span>1</span>\n    \n  \n    \n""" in rv.data
        assert """<a href="/?page=2">2</a>\n    \n  \n    \n""" in rv.data      
        assert """<a href="/?page=3">3</a>\n    \n  \n    \n""" in rv.data      
        assert """<a href="/?page=4">4</a>\n    \n  \n    \n""" in rv.data      
        assert """<span>...</span>\n    \n  \n    \n""" in rv.data      
        assert """<a href="/?page=15">15</a>\n    \n  \n    \n""" in rv.data
        assert """<a href="/?page=16">16</a>\n    \n  \n    \n""" in rv.data
        assert """<a href="/?page=17">17</a>\n    \n  \n    \n""" in rv.data      
        assert """<a href="/?page=18">18</a>\n    \n  \n  \n""" in rv.data    
        assert """<a href="/?page=2">next \xe2\x80\xba\xe2\x80\xba</a>\n  </div>""" in rv.data

        # TODO Write all pagination cases


if __name__ == '__main__':
    unittest.main()

# -*:- coding: utf-8 -*-
"""

    Blog Tests
    ~~~~~~~~~~


    Tests the blog application.

    :copyright: © 2010 by Gianluca Bargelli.
    :license: MIT, see LICENSE for more details.
"""

import os
import unittest
import tempfile
import datetime
from proudlygeek import blog


class BlogTestCase(unittest.TestCase):

    def setUp(self):
        """Before each test, set up a sample database"""
        self.db_fd, blog.app.config['DATABASE'] = tempfile.mkstemp()
        self.app = blog.app.test_client()
        blog.init_db(testdb=True)

    def tearDown(self):
        """Get rid of the database again after each test."""
        os.close(self.db_fd)
        os.unlink(blog.app.config['DATABASE'])

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
        assert """%s this is a test!""" \
               % (today.strftime('%Y-%m-%d')) in rv.data
        assert """<a href = /articles/%s/%s/%s/%s>Test Title</a>""" \
               % (today.year, today.month, today.day, 'this-is-a-test')
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
        rv = blog.slugify_entry(u"""!!"£$%&/()=?^'[]@#`<>'"%ciao mondo!""")
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

if __name__ == '__main__':
    unittest.main()

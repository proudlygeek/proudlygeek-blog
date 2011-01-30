# -*- coding: utf-8 -*-
"""

    blog.helpers
    ~~~~~~~~~~~~~~~~~~

    This module contains helper functions used for keep
    clean (and to write less code) the views module.

    :copyright: (c) 2010 by Gianluca Bargelli.
    :license: MIT License, see LICENSE for more details.


"""

from views import app
from flask import g, Markup, url_for 
import math
import hashlib
import datetime
import re
import markdown
from unicodedata import normalize


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
    try:
        #SQLite
        year, month, day = entry['creation_date'].split('-')
    except:
        #GAE
        year = str(entry['creation_date'].year)
        month = str(entry['creation_date'].month)
        day = str(entry['creation_date'].day)

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


def fill_markdown_content(entries, gen_readmore=True):
    """
    Convenience function which converts entry's body Markdown
    syntax to HTML code.
    """
    
    if len(entries) == 1:
        single = True
    else:
        single = False

    for entry in entries:
        entry['content'] = Markup(markdown.markdown(entry['body'], ['codehilite']))
        if gen_readmore: 
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
    fill_author(entries)


def filter_projects(entries):
    """
    Removes an entry from the list if it contains the tag "project";
    this is useful for not displaying my projects on list_entries.html
    without writing another template/function for this purpose.
    """
    for entry in entries:
        if 'project' in entry['tags']:
            entries.remove(entry)


def generate_page_title(tagname):
    """
    Generates an appropriate title string given a page's
    tag following these rules:

    1) "Blog" if tagname is None;
    2) "Entries tagged ``tag_test"" if tagname is not None;
    3) <entry.title> if len(entries) ==  1 (*)
    
    (*) Single entry title case is handled directly into the 
    views.view_entry method.
    """
    if tagname:
        if tagname == "project":
            title = """Projects"""
        else:
            title = u'Entries tagged “%s”' % (tagname)
    else:
        title = """Blog"""

    return title


def entry_pages(num_entries):
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
    max_page_entries = app.config['MAX_PAGE_ENTRIES']*1.0

    try:
        entry_pages = int(math.ceil(num_entries/max_page_entries))
    except ZeroDivisionError:
        print "Critical Error (Is MAX_PAGE_ENTRIES zero?): %s"

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

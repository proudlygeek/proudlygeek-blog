# -*- coding: utf-8 -*-
from blog import app


def main():
    if app.config['PLATFORM']=='sqlite':
        try:
            import sqlite3
        except:
            raise NameError("Sqlite3 module not found.")

        app.run()

    elif app.config['PLATFORM']=='gae':
        try:
            from google.appengine.ext.webapp.util import run_wsgi_app
        except:
            raise NameError ("Google App Engine SDK module not found.")

        run_wsgi_app(app)

if __name__ == '__main__':
    main()

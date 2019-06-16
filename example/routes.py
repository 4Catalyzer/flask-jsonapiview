# example/routes.py

from flask_resty import Api

from . import app, views

api = Api(app, "/api")

api.add_resource("/authors/", views.AuthorListView, views.AuthorListView)
api.add_resource("/books/", views.BookListView, views.BookView)
api.add_ping("/ping/")
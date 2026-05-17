from django.urls import path
from . import views

urlpatterns = [
    path("books/", views.books),
 ##  GET /api/books/?author=Rowling
# title
# -title
# author
# published_year

## POST /api/books/
# {
#     "title":"Test książka tytuł",
#     "author":"Test książka autor",
#     "published_year":2026
# }

    path("books/<int:pk>/", views.book_detail),
#GET /api/books/1/
#PUT /api/books/1/
# {
#     "title":"Test zmiany tytułu",
#     "author":"Inny autor",
#     "published_year":2025
# }

    path("fetch-books/", views.fetch_books),
    path("export-books/", views.export_books),
    path("import-books/", views.import_books),
    path("register/", views.register_user),
# {
#     "username":"user3",
#     "password":"test123"
# }

    path("login/", views.login_user),
# {
#     "username":"user3",
#     "password":"test123"
# }

    path("logout/", views.logout_user),
]
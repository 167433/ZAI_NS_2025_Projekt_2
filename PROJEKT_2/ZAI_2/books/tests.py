import json
import os
from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.conf import settings

from .models import Book, Category, ReadingEntry


class BookAPITest(TestCase):

    def setUp(self):
        self.client = Client()

        # 👤 users
        self.user1 = User.objects.create_user(
            username="user1",
            password="test123"
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="test123"
        )

    # =========================================================
    # AUTH TESTS
    # =========================================================

    def test_register_user(self):
        response = self.client.post(
            "/api/register/",
            data=json.dumps({
                "username": "newuser",
                "password": "test123"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            User.objects.filter(username="newuser").exists()
        )

    def test_login_user(self):
        response = self.client.post(
            "/api/login/",
            data=json.dumps({
                "username": "user1",
                "password": "test123"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

    def test_logout_user(self):
        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.post("/api/logout/")

        self.assertEqual(response.status_code, 200)

    # =========================================================
    # CRUD TESTS
    # =========================================================

    def test_create_book(self):
        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.post(
            "/api/books/",
            data=json.dumps({
                "title": "Harry Potter",
                "author": "Rowling",
                "published_year": 1997
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Book.objects.count(), 1)

    def test_get_books(self):
        Book.objects.create(
            title="Book 1",
            author="Author",
            owner=self.user1
        )

        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.get("/api/books/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_update_book(self):
        self.client.login(
            username="user1",
            password="test123"
        )

        book = Book.objects.create(
            title="Old",
            author="Author",
            owner=self.user1
        )

        response = self.client.put(
            f"/api/books/{book.id}/",
            data=json.dumps({
                "title": "New Title",
                "author": "New Author"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        book.refresh_from_db()

        self.assertEqual(book.title, "New Title")

    def test_delete_book(self):
        self.client.login(
            username="user1",
            password="test123"
        )

        book = Book.objects.create(
            title="To delete",
            author="Author",
            owner=self.user1
        )

        response = self.client.delete(
            f"/api/books/{book.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Book.objects.count(), 0)

    # =========================================================
    # OWNERSHIP TESTS
    # =========================================================

    def test_user_sees_only_own_books(self):

        Book.objects.create(
            title="User1 Book",
            author="A",
            owner=self.user1
        )

        Book.objects.create(
            title="User2 Book",
            author="B",
            owner=self.user2
        )

        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.get("/api/books/")

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "User1 Book")

    def test_user_cannot_update_other_user_book(self):

        book = Book.objects.create(
            title="Protected",
            author="Author",
            owner=self.user1
        )

        self.client.login(
            username="user2",
            password="test123"
        )

        response = self.client.put(
            f"/api/books/{book.id}/",
            data=json.dumps({
                "title": "Hacked"
            }),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_other_user_book(self):

        book = Book.objects.create(
            title="Protected",
            author="Author",
            owner=self.user1
        )

        self.client.login(
            username="user2",
            password="test123"
        )

        response = self.client.delete(
            f"/api/books/{book.id}/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Book.objects.filter(id=book.id).exists()
        )

    # =========================================================
    # FILTERING + SORTING TESTS
    # =========================================================

    def test_filter_books_by_author(self):

        Book.objects.create(
            title="HP",
            author="Rowling",
            owner=self.user1
        )

        Book.objects.create(
            title="LOTR",
            author="Tolkien",
            owner=self.user1
        )

        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.get(
            "/api/books/?author=Rowling"
        )

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["author"], "Rowling")

    def test_search_books(self):

        Book.objects.create(
            title="Harry Potter",
            author="Rowling",
            owner=self.user1
        )

        Book.objects.create(
            title="LOTR",
            author="Tolkien",
            owner=self.user1
        )

        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.get(
            "/api/books/?search=Harry"
        )

        data = response.json()

        self.assertEqual(len(data), 1)

    def test_order_books(self):

        Book.objects.create(
            title="Z Book",
            author="A",
            owner=self.user1
        )

        Book.objects.create(
            title="A Book",
            author="A",
            owner=self.user1
        )

        self.client.login(
            username="user1",
            password="test123"
        )

        response = self.client.get(
            "/api/books/?ordering=title"
        )

        data = response.json()

        self.assertEqual(
            data[0]["title"],
            "A Book"
        )

    # =========================================================
    # IMPORT / EXPORT TESTS
    # =========================================================

    def test_export_books(self):

        self.client.login(
            username="user1",
            password="test123"
        )

        category = Category.objects.create(
            name="Fantasy"
        )

        book = Book.objects.create(
            title="HP",
            author="Rowling",
            owner=self.user1
        )

        book.categories.add(category)

        response = self.client.get(
            "/api/export-books/"
        )

        self.assertEqual(response.status_code, 200)

        filename = response.json()["file"]

        backup_path = os.path.join(
            settings.BASE_DIR,
            "backups",
            filename
        )

        self.assertTrue(os.path.exists(backup_path))

    def test_import_books(self):

        self.client.login(
            username="user1",
            password="test123"
        )

        # fake backup
        backup_data = {
            "categories": [
                {"name": "Fantasy"}
            ],
            "books": [
                {
                    "title": "Imported Book",
                    "author": "Author",
                    "published_year": 2000,
                    "external_id": "123",
                    "categories": ["Fantasy"]
                }
            ],
            "reading_entries": []
        }

        backup_dir = os.path.join(
            settings.BASE_DIR,
            "backups"
        )

        os.makedirs(backup_dir, exist_ok=True)

        filename = "test_backup.json"

        filepath = os.path.join(
            backup_dir,
            filename
        )

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f)

        response = self.client.post(
            f"/api/import-books/?file={filename}"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Book.objects.count(), 1)

        self.assertTrue(
            Category.objects.filter(
                name="Fantasy"
            ).exists()
        )

@patch("books.views.fetch_books_from_api")
def test_fetch_books_anonymous_no_save(self, mock_fetch):

    mock_fetch.return_value = [
        {
            "external_id": "OL123",
            "title": "Harry Potter",
            "author": "Rowling",
            "year": 1997
        }
    ]

    response = self.client.get(
        "/api/fetch-books/?q=harry"
    )

    self.assertEqual(response.status_code, 200)

    # ❌ nic nie zapisano
    self.assertEqual(Book.objects.count(), 0)

    # ✔ dane zwrócone
    data = response.json()

    self.assertEqual(len(data), 1)
    self.assertEqual(data[0]["title"], "Harry Potter")

@patch("books.views.fetch_books_from_api")
def test_fetch_books_logged_user_save(self, mock_fetch):

    mock_fetch.return_value = [
        {
            "external_id": "OL123",
            "title": "Harry Potter",
            "author": "Rowling",
            "year": 1997
        }
    ]

    self.client.login(
        username="user1",
        password="test123"
    )

    response = self.client.get(
        "/api/fetch-books/?q=harry"
    )

    self.assertEqual(response.status_code, 200)

    # ✔ zapisano książkę
    self.assertEqual(Book.objects.count(), 1)

    book = Book.objects.first()

    self.assertEqual(book.owner, self.user1)
    self.assertEqual(book.title, "Harry Potter")
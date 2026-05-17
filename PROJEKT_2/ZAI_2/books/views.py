import io
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Book, Category, ReadingEntry
from .validators import validate_book
from .utils import get_test_user
from .services import fetch_books_from_api
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout


# 📚 LIST + CREATE
@csrf_exempt
def books(request):
    user = request.user

    if request.method == "GET":
        qs = Book.objects.filter(owner=user)

        # 🔍 filtrowanie
        author = request.GET.get("author")
        if author:
            qs = qs.filter(author__icontains=author)

        title = request.GET.get("search")
        if title:
            qs = qs.filter(title__icontains=title)

        # 🔽 sortowanie
        ordering = request.GET.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        data = []
        for b in qs:
            data.append({
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "year": b.published_year
            })

        return JsonResponse(data, safe=False)

    if request.method == "POST":

        if not request.user.is_authenticated:
            return JsonResponse({
                "error": "Authentication required"
            }, status=401)

        body = json.loads(request.body)

        book = Book.objects.create(
            title=body["title"],
            author=body["author"],
            published_year=body.get("published_year"),
            owner=request.user  # 🔥 TU
        )

        return JsonResponse({"id": book.id}, status=201)
    
@csrf_exempt
def book_detail(request, pk):

    if not request.user.is_authenticated:
        return JsonResponse({
            "error": "Authentication required"
        }, status=401)

    try:
        book = Book.objects.get(
            pk=pk,
            owner=request.user
        )

    except Book.DoesNotExist:
        return JsonResponse({
            "error": "Not found"
        }, status=404)

    # 📖 GET
    if request.method == "GET":
        return JsonResponse({
            "id": book.id,
            "title": book.title,
            "author": book.author
        })

    # ✏ UPDATE
    if request.method == "PUT":
        body = json.loads(request.body)

        book.title = body.get("title", book.title)
        book.author = body.get("author", book.author)
        book.published_year = body.get(
            "published_year",
            book.published_year
        )

        book.save()

        return JsonResponse({
            "message": "Updated"
        })

    # ❌ DELETE
    if request.method == "DELETE":
        book.delete()

        return JsonResponse({
            "message": "Deleted"
        })
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def fetch_books(request):

    query = request.GET.get("q")

    if not query:
        return JsonResponse({
            "error": "Query param 'q' required"
        }, status=400)

    try:
        books_data = fetch_books_from_api(query)

        # 👤 niezalogowany → tylko zwracamy dane
        if not request.user.is_authenticated:
            return JsonResponse(books_data, safe=False)

        # 👤 zalogowany → zapisujemy
        created = []

        for item in books_data:

            book, _ = Book.objects.get_or_create(
                external_id=item["external_id"],
                owner=request.user,
                defaults={
                    "title": item["title"],
                    "author": item["author"],
                    "published_year": item["year"],
                }
            )

            created.append({
                "id": book.id,
                "title": book.title
            })

        return JsonResponse(created, safe=False)

    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)
    
import os
import json
from datetime import datetime
from django.conf import settings


def export_books(request):
    user = request.user

    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    filename = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(backup_dir, filename)

    # 🔥 CATEGORY
    categories = list(Category.objects.values("id", "name"))

    # 🔥 BOOKS + M2M
    books = []
    for b in Book.objects.filter(owner=user):
        books.append({
            "title": b.title,
            "author": b.author,
            "published_year": b.published_year,
            "external_id": b.external_id,
            "categories": list(b.categories.values_list("name", flat=True))
        })

    # 🔥 READING ENTRIES
    entries = []
    for e in ReadingEntry.objects.filter(user=user):
        entries.append({
            "book_external_id": e.book.external_id,
            "status": e.status,
            "rating": e.rating,
            "notes": e.notes
        })

    data = {
        "categories": categories,
        "books": books,
        "reading_entries": entries
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return JsonResponse({
        "message": "Full backup created",
        "file": filename
    })

from django.db import transaction

from django.db import transaction


@csrf_exempt
@require_http_methods(["POST"])
def import_books(request):
    filename = request.GET.get("file")

    if not filename:
        return JsonResponse({"error": "file param required"}, status=400)

    if ".." in filename:
        return JsonResponse({"error": "Invalid filename"}, status=400)

    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    filepath = os.path.join(backup_dir, filename)

    if not os.path.exists(filepath):
        return JsonResponse({"error": "File not found"}, status=404)

    user = request.user

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        with transaction.atomic():

            # 🔥 CLEAR ALL (FULL RESTORE)
            ReadingEntry.objects.filter(user=user).delete()
            Book.objects.filter(owner=user).delete()
            Category.objects.all().delete()

            # 🔥 CATEGORIES
            category_map = {}
            for c in data.get("categories", []):
                obj = Category.objects.create(name=c["name"])
                category_map[c["name"]] = obj

            # 🔥 BOOKS
            book_map = {}

            for b in data.get("books", []):
                book = Book.objects.create(
                    title=b["title"],
                    author=b["author"],
                    published_year=b.get("published_year"),
                    external_id=b.get("external_id"),
                    owner=user
                )

                cats = [
                    category_map[name]
                    for name in b.get("categories", [])
                    if name in category_map
                ]
                book.categories.set(cats)

                book_map[book.external_id] = book

            # 🔥 READING ENTRIES
            for e in data.get("reading_entries", []):
                book = book_map.get(e["book_external_id"])

                if book:
                    ReadingEntry.objects.create(
                        book=book,
                        user=user,
                        status=e["status"],
                        rating=e.get("rating"),
                        notes=e.get("notes", "")
                    )

        return JsonResponse({"message": "Full restore completed"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    body = json.loads(request.body)

    username = body.get("username")
    password = body.get("password")

    if not username or not password:
        return JsonResponse({
            "error": "username and password required"
        }, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            "error": "User already exists"
        }, status=400)

    user = User.objects.create_user(
        username=username,
        password=password
    )

    return JsonResponse({
        "message": "User created",
        "id": user.id
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    body = json.loads(request.body)

    username = body.get("username")
    password = body.get("password")

    user = authenticate(
        request,
        username=username,
        password=password
    )

    if user is None:
        return JsonResponse({
            "error": "Invalid credentials"
        }, status=401)

    login(request, user)

    return JsonResponse({
        "message": "Logged in"
    })

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout


@csrf_exempt
@require_http_methods(["POST"])
def logout_user(request):
    logout(request)

    return JsonResponse({
        "message": "Logged out"
    })
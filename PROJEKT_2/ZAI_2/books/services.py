import requests


def fetch_books_from_api(query):
    url = f"https://openlibrary.org/search.json?q={query}"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    books = []

    for item in data.get("docs", [])[:10]:  # limit 10
        books.append({
            "title": item.get("title"),
            "author": item.get("author_name", ["Unknown"])[0],
            "year": item.get("first_publish_year"),
            "external_id": item.get("key")
        })

    return books
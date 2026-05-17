def validate_book(data):
    errors = {}

    if not data.get("title"):
        errors["title"] = "Required"

    if not data.get("author"):
        errors["author"] = "Required"

    return errors
import os
import shutil
import json
from app import app, get_categories, get_articles_in_category


def save_html(rel_path: str, html: str):
    root = os.path.join("docs", rel_path.strip("/"))
    if rel_path.endswith("/"):
        dest_dir = root
        os.makedirs(dest_dir, exist_ok=True)
        out_path = os.path.join(dest_dir, "index.html")
    else:
        os.makedirs(os.path.dirname(root), exist_ok=True)
        out_path = root
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    if os.path.exists("docs"):
        shutil.rmtree("docs")
    os.makedirs("docs", exist_ok=True)

    with app.test_client() as client:
        save_html("/", client.get("/").data.decode("utf-8"))
        save_html("/about/", client.get("/about").data.decode("utf-8"))
        save_html("/search/", client.get("/search").data.decode("utf-8"))

        for cat in get_categories():
            save_html(f"/{cat}/", client.get(f"/{cat}/").data.decode("utf-8"))
            for art in get_articles_in_category(cat):
                save_html(
                    f"/{cat}/{art['slug']}/",
                    client.get(f"/{cat}/{art['slug']}").data.decode("utf-8"),
                )
    categories = get_categories()
    index = []
    for cat in categories:
        for art in get_articles_in_category(cat):
            index.append({
                "title": art["title"],
                "subtitle": art.get("subtitle", ""),
                "summary": art.get("summary", ""),
                "author": art.get("author", ""),
                "date": art.get("date", ""),
                "category": art["category"],
                "slug": art["slug"],
                "url": f"/{art['category']}/{art['slug']}/"
            })
    with open(os.path.join("docs", "index.json"), "w", encoding="utf-8") as jf:
        json.dump(index, jf, ensure_ascii=False, indent=2)

    shutil.copyfile("home.JPG", os.path.join("docs", "home.JPG"))


if __name__ == "__main__":
    main()

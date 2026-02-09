import os
import shutil
import json
from app import app, get_categories, get_articles_in_category, ARTICLES_DIR


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
    with open(os.path.join("docs", ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

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
            # Determine cover_url
            cover_url = ""
            cov = (art.get("cover") or "").strip()
            base_dir = os.path.join(ARTICLES_DIR, cat)
            covers_out_dir = os.path.join("docs", "covers", cat)
            os.makedirs(covers_out_dir, exist_ok=True)
            def copy_and_url(fname):
                src = os.path.join(base_dir, fname)
                if os.path.exists(src):
                    shutil.copyfile(src, os.path.join(covers_out_dir, fname))
                    return f"/covers/{cat}/{fname}"
                return ""
            if cov.startswith("http://") or cov.startswith("https://"):
                cover_url = cov
            elif cov:
                fname = os.path.basename(cov)
                cover_url = copy_and_url(fname)
            if not cover_url:
                for ext in ["jpg", "jpeg", "png", "webp"]:
                    fname = f"{art['slug']}.{ext}"
                    cover_url = copy_and_url(fname)
                    if cover_url:
                        break
            if not cover_url:
                for ext in ["jpg", "jpeg", "png", "webp"]:
                    fname = f"cover.{ext}"
                    cover_url = copy_and_url(fname)
                    if cover_url:
                        break
            index.append({
                "title": art["title"],
                "subtitle": art.get("subtitle", ""),
                "summary": art.get("summary", ""),
                "author": art.get("author", ""),
                "date": art.get("date", ""),
                "category": art["category"],
                "slug": art["slug"],
                "url": f"/{art['category']}/{art['slug']}/",
                "cover_url": cover_url,
                "featured": bool(art.get("featured"))
            })
    with open(os.path.join("docs", "index.json"), "w", encoding="utf-8") as jf:
        json.dump(index, jf, ensure_ascii=False, indent=2)

    # Copy all images from articles directory to docs/covers
    for cat in get_categories():
        src_cat_dir = os.path.join(ARTICLES_DIR, cat)
        dest_covers_dir = os.path.join("docs", "covers", cat)
        os.makedirs(dest_covers_dir, exist_ok=True)
        
        for root, dirs, files in os.walk(src_cat_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, src_cat_dir)
                    dest_file = os.path.join(dest_covers_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copyfile(src_file, dest_file)

    shutil.copyfile("home.JPG", os.path.join("docs", "home.JPG"))
    shutil.copyfile("logo.png", os.path.join("docs", "logo.png"))


if __name__ == "__main__":
    main()

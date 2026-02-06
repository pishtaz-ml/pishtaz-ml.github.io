from flask_frozen import Freezer
from app import app, get_categories, get_articles_in_category

freezer = Freezer(app)

@freezer.register_generator
def category_page():
    for cat in get_categories():
        yield {'category': cat}

@freezer.register_generator
def article_page():
    for cat in get_categories():
        for art in get_articles_in_category(cat):
            yield {'category': cat, 'slug': art['slug']}

if __name__ == '__main__':
    freezer.freeze()

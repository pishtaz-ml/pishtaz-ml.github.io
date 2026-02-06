import os
import re
import markdown
import bleach
from flask import Flask, render_template, abort, request, send_file, url_for
from datetime import datetime

app = Flask(__name__)
ARTICLES_DIR = 'articles'
BASE_PATH = os.environ.get('BASE_PATH', '')

def get_categories():
    """Returns a list of category names based on subdirectories in ARTICLES_DIR."""
    if not os.path.exists(ARTICLES_DIR):
        return []
    return sorted([d for d in os.listdir(ARTICLES_DIR) 
                   if os.path.isdir(os.path.join(ARTICLES_DIR, d)) and not d.startswith('.')])

def get_article_metadata(category, filename):
    """Parses markdown file metadata."""
    filepath = os.path.join(ARTICLES_DIR, category, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    md = markdown.Markdown(extensions=['meta'])
    md.convert(text)
    
    meta = md.Meta
    # Helper to get single value or default
    title = meta.get('title', [filename.replace('.md', '').replace('-', ' ').title()])[0]
    date_str = meta.get('date', [''])[0]
    summary = meta.get('summary', [''])[0]
    author = meta.get('author', ['ناشناس'])[0]
    subtitle = meta.get('subtitle', [''])[0]
    
    date_obj = None
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            pass
            
    return {
        'title': title,
        'date': date_str,
        'date_obj': date_obj,
        'summary': summary,
        'author': author,
        'subtitle': subtitle,
        'category': category,
        'slug': filename.replace('.md', '')
    }

def get_articles_in_category(category):
    """Returns list of articles in a category."""
    cat_dir = os.path.join(ARTICLES_DIR, category)
    if not os.path.exists(cat_dir):
        return []
    
    files = [f for f in os.listdir(cat_dir) if f.endswith('.md')]
    articles = []
    for f in files:
        articles.append(get_article_metadata(category, f))
    
    # Sort by date descending
    articles.sort(key=lambda x: x['date_obj'] or datetime.min, reverse=True)
    return articles

def get_all_articles():
    """Returns all articles from all categories."""
    categories = get_categories()
    all_articles = []
    for cat in categories:
        all_articles.extend(get_articles_in_category(cat))
    
    all_articles.sort(key=lambda x: x['date_obj'] or datetime.min, reverse=True)
    return all_articles

def search_articles(query):
    """Searches for query in article titles and content."""
    query = query.lower()
    results = []
    categories = get_categories()
    
    for category in categories:
        cat_dir = os.path.join(ARTICLES_DIR, category)
        if not os.path.exists(cat_dir):
            continue
            
        files = [f for f in os.listdir(cat_dir) if f.endswith('.md')]
        for f in files:
            filepath = os.path.join(cat_dir, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse metadata to get title
            md = markdown.Markdown(extensions=['meta'])
            md.convert(content)
            meta = md.Meta
            title = meta.get('title', [f.replace('.md', '').replace('-', ' ').title()])[0]
            
            # Check if query is in title or content
            if query in title.lower() or query in content.lower():
                # Re-use get_article_metadata to get formatted dict
                article_data = get_article_metadata(category, f)
                results.append(article_data)
                
    return results

@app.context_processor
def inject_categories():
    """Inject categories into all templates."""
    def path_for(endpoint, **values):
        return f"{BASE_PATH}{url_for(endpoint, **values)}"
    return dict(categories=get_categories(), base_path=BASE_PATH, path_for=path_for)

@app.route('/')
def index():
    articles = get_all_articles()
    return render_template('index.html', articles=articles)

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search.html', query=query, articles=[])
    
    articles = search_articles(query)
    return render_template('search.html', query=query, articles=articles)

@app.route('/<category>/')
def category_page(category):
    if category not in get_categories():
        abort(404)
    articles = get_articles_in_category(category)
    return render_template('category.html', category=category, articles=articles)

def _safe_article_path(category: str, slug: str) -> str:
    if category not in get_categories():
        abort(404)
    if not slug or '..' in slug or slug.startswith('.'):
        abort(400)
    base_dir = os.path.abspath(os.path.join(ARTICLES_DIR, category))
    candidate = os.path.abspath(os.path.join(base_dir, slug + '.md'))
    if not candidate.startswith(base_dir + os.sep):
        abort(400)
    return candidate

ALLOWED_TAGS = [
    'p','h1','h2','h3','h4','h5','h6','strong','em',
    'ul','ol','li','blockquote','code','pre',
    'table','thead','tbody','tr','th','td',
    'a','img'
]
ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel', 'target'],
    'img': ['src', 'alt', 'title', 'loading'],
    'th': ['align'],
    'td': ['align'],
    'code': ['class'],
    'pre': ['class'],
}
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

@app.route('/<category>/<slug>')
def article_page(category, slug):
    filepath = _safe_article_path(category, slug)
    if not os.path.exists(filepath):
        abort(404)
        
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
        
    md = markdown.Markdown(extensions=['meta', 'fenced_code', 'tables'])
    html = md.convert(text)
    safe_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    meta = md.Meta
    title = meta.get('title', [slug.replace('-', ' ').title()])[0]
    date = meta.get('date', [''])[0]
    author = meta.get('author', ['ناشناس'])[0]
    subtitle = meta.get('subtitle', [''])[0]
    
    return render_template('article.html', 
                           content=safe_html, 
                           title=title, 
                           date=date, 
                           author=author,
                           subtitle=subtitle,
                           category=category)

@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'interest-cohort=()'
    return response

@app.route('/home.JPG')
def serve_home_image():
    path = os.path.abspath('/Users/faridounet/Research/Pishtaz/home.JPG')
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(debug=True, port=3000)

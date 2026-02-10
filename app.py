import os
import re
import markdown
import bleach
from flask import Flask, render_template, abort, request, send_file, url_for
from flask import jsonify
from datetime import datetime

app = Flask(__name__)
ARTICLES_DIR = 'articles'
# Default to production URL if not set
BASE_URL = os.environ.get('BASE_URL', 'https://pishtaz-ml.github.io').rstrip('/')
IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp']

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
    cover = meta.get('cover', [''])[0]
    featured_raw = meta.get('featured', [''])[0].strip().lower()
    featured = featured_raw in ('true', 'yes', '1', 'on')
    
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
        'slug': filename.replace('.md', ''),
        'cover': cover,
        'featured': featured
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

def article_cover_url(article):
    cov = (article.get('cover') or '').strip()
    if cov.startswith('http://') or cov.startswith('https://'):
        return cov
    cat = article['category']
    slug = article['slug']
    base_dir = os.path.join(ARTICLES_DIR, cat)
    if cov:
        # Support nested paths like 'image/cover.png'
        candidate = os.path.abspath(os.path.join(base_dir, cov))
        if os.path.exists(candidate) and candidate.startswith(os.path.abspath(base_dir) + os.sep):
            return f"{BASE_URL}/covers/{cat}/{cov}"
    # Fallback to older behavior (looking for filename only)
    if cov:
        fname = os.path.basename(cov)
        candidate = os.path.abspath(os.path.join(base_dir, fname))
        if os.path.exists(candidate):
            return f"{BASE_URL}/covers/{cat}/{fname}"
    for ext in IMAGE_EXTS:
        # Check image/{slug}/cover.{ext}
        fname = os.path.join('image', slug, f"cover.{ext}")
        candidate = os.path.abspath(os.path.join(base_dir, fname))
        if os.path.exists(candidate):
            return f"{BASE_URL}/covers/{cat}/{fname}"
        # Check image/{slug}/{slug}.{ext}
        fname = os.path.join('image', slug, f"{slug}.{ext}")
        candidate = os.path.abspath(os.path.join(base_dir, fname))
        if os.path.exists(candidate):
            return f"{BASE_URL}/covers/{cat}/{fname}"
        # Check {slug}.{ext} in category root
        fname = f"{slug}.{ext}"
        candidate = os.path.abspath(os.path.join(base_dir, fname))
        if os.path.exists(candidate):
            return f"{BASE_URL}/covers/{cat}/{fname}"
    for ext in IMAGE_EXTS:
        # Check cover.{ext} in category root
        fname = f"cover.{ext}"
        candidate = os.path.abspath(os.path.join(base_dir, fname))
        if os.path.exists(candidate):
            return f"{BASE_URL}/covers/{cat}/{fname}"
    return ''

@app.context_processor
def inject_categories():
    """Inject categories into all templates."""
    def path_for(endpoint, **values):
        p = url_for(endpoint, **values)
        if p != '/' and not p.endswith('/'):
            p = p + '/'
        return f"{BASE_URL}{p}"
    return dict(categories=get_categories(),
                path_for=path_for,
                base_url=BASE_URL,
                article_cover_url=article_cover_url,
                now_year=datetime.now().year)

@app.route('/')
def index():
    all_articles = get_all_articles()
    featured_articles = [a for a in all_articles if a.get('featured')][:6]
    latest_articles = all_articles[:12]
    return render_template('index.html', articles=latest_articles, featured_articles=featured_articles)

@app.route('/about')
@app.route('/about/')
def about():
    return render_template('about.html')
@app.route('/search')
@app.route('/search/')
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
    'a','img','sup','div','span','section','small','hr',
    'figure', 'figcaption'
]
ALLOWED_ATTRS = {
    'a': ['href', 'title', 'rel', 'target', 'id', 'class'],
    'img': ['src', 'alt', 'title', 'loading', 'class'],
    'th': ['align', 'class'],
    'td': ['align', 'class'],
    'code': ['class'],
    'pre': ['class'],
    'sup': ['id', 'class'],
    'div': ['id', 'class'],
    'li': ['id', 'class'],
    'ol': ['class'],
    'span': ['id', 'class'],
    'section': ['id', 'class'],
    'small': ['class'],
    'h1': ['id', 'class'],
    'h2': ['id', 'class'],
    'h3': ['id', 'class'],
    'h4': ['id', 'class'],
    'h5': ['id', 'class'],
    'h6': ['id', 'class'],
    'figure': ['class'],
    'figcaption': ['class']
}
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

@app.route('/<category>/<slug>')
@app.route('/<category>/<slug>/')
def article_page(category, slug):
    filepath = _safe_article_path(category, slug)
    if not os.path.exists(filepath):
        abort(404)
        
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Pre-process markdown to fix image paths
    # Replace ![alt](image/...) with ![alt](/covers/category/image/...)
    # Replace ![alt](filename.png) with ![alt](/covers/category/filename.png)
    def fix_img_path(match):
        alt = match.group(1)
        path = match.group(2)
        if path.startswith('http') or path.startswith('/'):
            full_path = path
        else:
            full_path = f'{BASE_URL}/covers/{category}/{path}'
        
        if alt and not alt.isdigit() and len(alt) > 3: 
            # If there's a caption (alt text) that isn't just a number and is long enough
            return f'<figure class="article-figure"><img src="{full_path}" alt="{alt}"><figcaption class="article-caption">{alt}</figcaption></figure>'
        return f'![{alt}]({full_path})'
    
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', fix_img_path, text)
        
    md = markdown.Markdown(extensions=['meta', 'fenced_code', 'tables', 'footnotes', 'toc'],
                           extension_configs={'toc': {'title': '', 'toc_class': 'toc-list'}})
    html = md.convert(text)
    toc_html = md.toc if hasattr(md, 'toc') else ''
    safe_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    # We also need to clean the TOC HTML if we use it, but TOC extension usually produces safe HTML with links and IDs.
    # However, to be safe, let's include it in the context.
    
    meta = md.Meta
    title = meta.get('title', [slug.replace('-', ' ').title()])[0]
    date = meta.get('date', [''])[0]
    author = meta.get('author', ['ناشناس'])[0]
    subtitle = meta.get('subtitle', [''])[0]
    summary = meta.get('summary', [''])[0]
    cover = article_cover_url({'category': category, 'slug': slug, 'cover': meta.get('cover', [''])[0]})
    
    return render_template('article.html', 
                           content=safe_html, 
                           toc=toc_html,
                           title=title, 
                           date=date, 
                           author=author,
                           subtitle=subtitle,
                           summary=summary,
                           cover=cover,
                           category=category)

@app.route('/index.json')
def index_json():
    items = []
    for a in get_all_articles():
        items.append({
            "title": a.get("title", ""),
            "subtitle": a.get("subtitle", ""),
            "summary": a.get("summary", ""),
            "author": a.get("author", ""),
            "date": a.get("date", ""),
            "category": a["category"],
            "slug": a["slug"],
            "url": f"/{a['category']}/{a['slug']}/"
        })
    return jsonify(items)

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
    path = os.path.join(app.root_path, 'home.JPG')
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype='image/jpeg')

@app.route('/logo.png')
def serve_logo():
    path = os.path.join(app.root_path, 'logo.png')
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype='image/png')

@app.route('/covers/<category>/<path:filename>')
def serve_cover_image(category, filename):
    if category not in get_categories():
        abort(404)
    if not filename or '..' in filename or filename.startswith('.'):
        abort(400)
    base_dir = os.path.abspath(os.path.join(ARTICLES_DIR, category))
    candidate = os.path.abspath(os.path.join(base_dir, filename))
    if not candidate.startswith(base_dir + os.sep):
        abort(400)
    if not os.path.exists(candidate):
        abort(404)
    ext = os.path.splitext(filename)[1].lower()
    mime = 'image/jpeg'
    if ext == '.png':
        mime = 'image/png'
    elif ext == '.webp':
        mime = 'image/webp'
    elif ext == '.gif':
        mime = 'image/gif'
    elif ext == '.svg':
        mime = 'image/svg+xml'
    return send_file(candidate, mimetype=mime)
if __name__ == '__main__':
    app.run(debug=True, port=3000)

# app.py - Working Movie Recommendation Website
from flask import Flask, render_template_string, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import sqlite3
from datetime import timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'xstar-super-secret-key-2024')
app.permanent_session_lifetime = timedelta(hours=24)

# ==================== Database Setup ====================
def init_db():
    """Initialize the database with tables."""
    db_path = os.environ.get('DATABASE_PATH', 'movies.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create favorites table
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        poster_path TEXT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, movie_id)
    )''')
    
    # Add default admin user if not exists
    try:
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                 ('admin', 'admin@xstar.com', generate_password_hash('admin123')))
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                 ('demo', 'demo@xstar.com', generate_password_hash('demo123')))
    except sqlite3.IntegrityError:
        pass  # Users already exist
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection."""
    db_path = os.environ.get('DATABASE_PATH', 'movies.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database on startup
init_db()

# ==================== Sample Movie Data ====================
TRENDING_MOVIES = [
    {"id": 1, "title": "Dune: Part Two", "year": "2024", "rating": 8.9, "poster": "🎬"},
    {"id": 2, "title": "Deadpool 3", "year": "2024", "rating": 8.7, "poster": "🎬"},
    {"id": 3, "title": "Kung Fu Panda 4", "year": "2024", "rating": 8.2, "poster": "🎬"},
    {"id": 4, "title": "Godzilla x Kong", "year": "2024", "rating": 8.5, "poster": "🎬"},
    {"id": 5, "title": "Inside Out 2", "year": "2024", "rating": 8.4, "poster": "🎬"},
    {"id": 6, "title": "Joker: Folie à Deux", "year": "2024", "rating": 8.6, "poster": "🎬"},
]

POPULAR_MOVIES = [
    {"id": 7, "title": "Oppenheimer", "year": "2023", "rating": 8.9, "poster": "🎬"},
    {"id": 8, "title": "Barbie", "year": "2023", "rating": 7.8, "poster": "🎬"},
    {"id": 9, "title": "The Marvels", "year": "2023", "rating": 7.2, "poster": "🎬"},
    {"id": 10, "title": "Wonka", "year": "2023", "rating": 7.9, "poster": "🎬"},
    {"id": 11, "title": "Napoleon", "year": "2023", "rating": 7.5, "poster": "🎬"},
    {"id": 12, "title": "The Creator", "year": "2023", "rating": 7.8, "poster": "🎬"},
]

RECOMMENDED_MOVIES = [
    {"id": 13, "title": "Inception", "year": "2010", "rating": 8.8, "poster": "🎬"},
    {"id": 14, "title": "The Dark Knight", "year": "2008", "rating": 9.0, "poster": "🎬"},
    {"id": 15, "title": "Interstellar", "year": "2014", "rating": 8.6, "poster": "🎬"},
    {"id": 16, "title": "Pulp Fiction", "year": "1994", "rating": 8.9, "poster": "🎬"},
]

# ==================== Authentication Decorator ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== Routes ====================
@app.route('/')
def index():
    """Home page with movie recommendations."""
    return render_template_string(MAIN_PAGE_TEMPLATE, 
                                trending=TRENDING_MOVIES,
                                popular=POPULAR_MOVIES,
                                recommended=RECOMMENDED_MOVIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", [username]).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user'] = user['username']
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template_string(LOGIN_PAGE_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    [username, email, generate_password_hash(password)]
                )
                conn.commit()
                user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.close()
                
                session.permanent = True
                session['user_id'] = user_id
                session['username'] = username
                session['user'] = username
                flash('Account created successfully!', 'success')
                return redirect(url_for('index'))
            except sqlite3.IntegrityError:
                flash('Username already exists.', 'danger')
                conn.close()
    
    return render_template_string(REGISTER_PAGE_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/search')
def search():
    """Search page."""
    query = request.args.get('q', '').lower()
    results = []
    
    if query:
        all_movies = TRENDING_MOVIES + POPULAR_MOVIES + RECOMMENDED_MOVIES
        results = [m for m in all_movies if query in m['title'].lower()]
    
    return render_template_string(SEARCH_PAGE_TEMPLATE, 
                                query=query, 
                                results=results)

@app.route('/recommendations')
def recommendations():
    """Recommendations page."""
    return render_template_string(RECOMMENDATIONS_PAGE_TEMPLATE, 
                                movies=RECOMMENDED_MOVIES + POPULAR_MOVIES[:6])

@app.route('/trending')
def trending():
    """Trending page."""
    return render_template_string(TRENDING_PAGE_TEMPLATE, 
                                movies=TRENDING_MOVIES)

@app.route('/favorites')
@login_required
def favorites():
    """User favorites page."""
    conn = get_db()
    favorites = conn.execute(
        "SELECT * FROM favorites WHERE user_id = ? ORDER BY added_at DESC",
        [session['user_id']]
    ).fetchall()
    conn.close()
    
    return render_template_string(FAVORITES_PAGE_TEMPLATE, favorites=favorites)

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    """Add movie to favorites."""
    data = request.get_json()
    movie_id = data.get('movie_id')
    movie_title = data.get('movie')
    
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?",
        [session['user_id'], movie_id]
    ).fetchone()
    
    if existing:
        conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
            [session['user_id'], movie_id]
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Removed from favorites!', 'action': 'removed'})
    else:
        conn.execute(
            "INSERT INTO favorites (user_id, movie_id, title) VALUES (?, ?, ?)",
            [session['user_id'], movie_id, movie_title]
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Added to favorites!', 'action': 'added'})

# ==================== Error Handlers ====================
@app.errorhandler(404)
def not_found_error(error):
    return render_template_string(ERROR_PAGE_TEMPLATE, 
                                error_code=404, 
                                error_message="Page Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template_string(ERROR_PAGE_TEMPLATE, 
                                error_code=500, 
                                error_message="Internal Server Error"), 500

# ==================== Templates ====================
MAIN_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X★STAR - AI Movie Recommendations</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        
        /* Header Styles */
        .header {
            position: relative;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            overflow: hidden;
            padding: 2rem;
        }
        
        .bg-animation {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(120,119,198,0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255,119,198,0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120,219,255,0.2) 0%, transparent 50%);
            animation: bgShift 20s ease infinite;
            z-index: -1;
        }
        
        @keyframes bgShift {
            0%, 100% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.1) rotate(180deg); }
        }
        
        .logo {
            font-size: 5rem; 
            font-weight: bold;
            background: linear-gradient(45deg, #00d4ff, #ff6b9d, #ffd93d, #00ff88);
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent;
            background-clip: text; 
            margin-bottom: 1rem;
            text-shadow: 0 0 40px rgba(0,212,255,0.6);
            animation: logoGlow 2.5s ease-in-out infinite alternate;
        }
        
        @keyframes logoGlow {
            from { filter: drop-shadow(0 0 30px #00d4ff); transform: scale(1); }
            to { filter: drop-shadow(0 0 40px #ffd93d); transform: scale(1.05); }
        }
        
        .tagline { 
            font-size: 1.8rem; 
            margin-bottom: 2.5rem; 
            opacity: 0.95; 
            animation: fadeInUp 1s ease 0.5s both; 
        }
        
        @keyframes fadeInUp { 
            from { opacity: 0; transform: translateY(30px); } 
            to { opacity: 0.95; transform: translateY(0); } 
        }
        
        /* Navigation */
        .nav-links { 
            display: flex; 
            gap: 2rem; 
            list-style: none; 
            margin-bottom: 2rem; 
            animation: fadeInUp 1s ease 0.2s both;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .nav-links a {
            color: rgba(255,255,255,0.9); 
            text-decoration: none; 
            font-weight: 600; 
            padding: 0.8rem 1.5rem;
            border-radius: 30px; 
            transition: all 0.3s ease; 
            backdrop-filter: blur(10px);
            background: rgba(255,255,255,0.05);
        }
        
        .nav-links a:hover { 
            background: rgba(0,212,255,0.2); 
            color: #00d4ff; 
            transform: translateY(-3px); 
            box-shadow: 0 10px 25px rgba(0,212,255,0.3); 
        }
        
        /* User Section */
        .user-section { 
            position: absolute; 
            top: 2rem; 
            right: 2rem; 
            display: flex; 
            gap: 1rem; 
            align-items: center;
            z-index: 10;
        }
        
        .user-btn { 
            background: rgba(0,212,255,0.2); 
            padding: 0.8rem 1.5rem; 
            border-radius: 25px; 
            text-decoration: none; 
            color: white; 
            font-weight: 600; 
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .user-btn:hover { 
            background: rgba(0,212,255,0.4); 
            transform: translateY(-2px); 
        }
        
        /* Search Container */
        .search-container {
            width: 65%; 
            max-width: 700px; 
            margin-bottom: 2rem; 
            animation: fadeInUp 1s ease 0.8s both;
            position: relative;
        }
        
        .search-box {
            width: 100%; 
            padding: 1.2rem 2rem; 
            font-size: 1.1rem; 
            border: 2px solid rgba(0,212,255,0.3);
            border-radius: 50px; 
            background: rgba(255,255,255,0.95); 
            box-shadow: 0 15px 40px rgba(0,0,0,0.4);
            outline: none; 
            transition: all 0.4s ease; 
            color: #333; 
            backdrop-filter: blur(10px);
        }
        
        .search-box:focus { 
            border-color: #00d4ff; 
            transform: scale(1.02); 
            box-shadow: 0 20px 50px rgba(0,212,255,0.3); 
        }
        
        .search-btn {
            position: absolute; 
            right: 5px; 
            top: 50%; 
            transform: translateY(-50%);
            background: linear-gradient(45deg, #00d4ff, #ff6b9d); 
            border: none; 
            padding: 0.8rem 1.8rem;
            border-radius: 50px; 
            color: white; 
            font-weight: bold; 
            font-size: 1rem; 
            cursor: pointer;
            transition: all 0.3s ease; 
            box-shadow: 0 5px 20px rgba(0,212,255,0.4);
        }
        
        .search-btn:hover { 
            transform: translateY(-50%) scale(1.05); 
            box-shadow: 0 10px 30px rgba(0,212,255,0.6); 
        }
        
        /* Features */
        .features { 
            display: flex; 
            gap: 3rem; 
            margin-top: 2rem;
            animation: fadeInUp 1s ease 1s both;
        }
        
        .feature-item { 
            text-align: center; 
            color: #ccc; 
        }
        
        .feature-item strong { 
            display: block; 
            font-size: 1.2rem; 
            color: #00d4ff; 
            margin-bottom: 0.3rem; 
        }
        
        /* Content Sections */
        .content { 
            padding: 4rem 2rem; 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        
        .section-title {
            font-size: 2.5rem;
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .movies-grid {
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 2rem; 
            margin-bottom: 3rem;
        }
        
        .movie-card {
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 1.5rem; 
            text-align: center;
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255,255,255,0.2); 
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .movie-card:hover { 
            transform: translateY(-10px); 
            box-shadow: 0 20px 40px rgba(0,212,255,0.3); 
        }
        
        .movie-poster {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .movie-title { 
            font-size: 1.2rem; 
            font-weight: bold; 
            margin-bottom: 0.5rem; 
            color: #00d4ff; 
        }
        
        .movie-year {
            color: #ccc;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        .movie-rating {
            color: #ffd93d;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        
        .favorite-btn {
            background: rgba(255,107,157,0.3);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .favorite-btn:hover {
            background: rgba(255,107,157,0.6);
            transform: scale(1.05);
        }
        
        /* Flash Messages */
        .flash-messages {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            max-width: 400px;
        }
        
        .flash {
            padding: 1rem 2rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            animation: slideDown 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .flash.success {
            background: rgba(0,255,136,0.2);
            border: 1px solid #00ff88;
            color: #00ff88;
        }
        
        .flash.danger {
            background: rgba(255,107,157,0.2);
            border: 1px solid #ff6b9d;
            color: #ff6b9d;
        }
        
        .flash.warning {
            background: rgba(255,217,61,0.2);
            border: 1px solid #ffd93d;
            color: #ffd93d;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .logo { font-size: 3rem; } 
            .tagline { font-size: 1.2rem; }
            .search-container { width: 95%; } 
            .nav-links { gap: 0.5rem; }
            .features { flex-direction: column; gap: 1rem; } 
            .user-section { top: 1rem; right: 1rem; flex-direction: column; }
            .section-title { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="flash-messages">
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Hero Section -->
    <div class="header">
        <div class="bg-animation"></div>
        
        <div class="user-section">
            {% if session.user %}
                <a href="/favorites" class="user-btn">⭐ {{ session.user }}'s Favorites</a>
                <a href="/logout" class="user-btn">Logout</a>
            {% else %}
                <a href="/login" class="user-btn">Login</a>
                <a href="/register" class="user-btn">Register</a>
            {% endif %}
        </div>
        
        <ul class="nav-links">
            <li><a href="/">🏠 Home</a></li>
            <li><a href="/recommendations">🎯 Recommendations</a></li>
            <li><a href="/trending">🔥 Trending</a></li>
            <li><a href="/search">🔍 Search</a></li>
        </ul>

        <div class="logo">X★STAR</div>
        <div class="tagline">Your AI Movie Recommendation Engine</div>
        
        <div class="search-container">
            <input type="text" class="search-box" placeholder="Search for movies..." id="searchInput">
            <button class="search-btn" onclick="performSearch()">🔍 Find Movies</button>
        </div>

        <div class="features">
            <div class="feature-item"><strong>10M+</strong> Movies</div>
            <div class="feature-item"><strong>AI Powered</strong> Matches</div>
            <div class="feature-item"><strong>Free Forever</strong></div>
        </div>
    </div>

    <!-- Content Sections -->
    <div class="content">
        <!-- Trending Section -->
        <h2 class="section-title">🔥 Trending Now</h2>
        <div class="movies-grid">
            {% for movie in trending %}
            <div class="movie-card" onclick="viewMovie({{ movie.id }})">
                <div class="movie-poster">{{ movie.poster }}</div>
                <div class="movie-title">{{ movie.title }}</div>
                <div class="movie-year">{{ movie.year }}</div>
                <div class="movie-rating">⭐ {{ movie.rating }}/10</div>
                <button class="favorite-btn" onclick="event.stopPropagation(); toggleFavorite({{ movie.id }}, '{{ movie.title }}')">
                    💖 Save
                </button>
            </div>
            {% endfor %}
        </div>
        
        <!-- Popular Section -->
        <h2 class="section-title">🎬 Popular Movies</h2>
        <div class="movies-grid">
            {% for movie in popular %}
            <div class="movie-card" onclick="viewMovie({{ movie.id }})">
                <div class="movie-poster">{{ movie.poster }}</div>
                <div class="movie-title">{{ movie.title }}</div>
                <div class="movie-year">{{ movie.year }}</div>
                <div class="movie-rating">⭐ {{ movie.rating }}/10</div>
                <button class="favorite-btn" onclick="event.stopPropagation(); toggleFavorite({{ movie.id }}, '{{ movie.title }}')">
                    💖 Save
                </button>
            </div>
            {% endfor %}
        </div>
        
        <!-- Recommended Section -->
        <h2 class="section-title">✨ Recommended For You</h2>
        <div class="movies-grid">
            {% for movie in recommended %}
            <div class="movie-card" onclick="viewMovie({{ movie.id }})">
                <div class="movie-poster">{{ movie.poster }}</div>
                <div class="movie-title">{{ movie.title }}</div>
                <div class="movie-year">{{ movie.year }}</div>
                <div class="movie-rating">⭐ {{ movie.rating }}/10</div>
                <button class="favorite-btn" onclick="event.stopPropagation(); toggleFavorite({{ movie.id }}, '{{ movie.title }}')">
                    💖 Save
                </button>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function performSearch() {
            const query = document.getElementById('searchInput').value;
            if (query.trim()) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        }
        
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') performSearch();
        });
        
        function toggleFavorite(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                } else {
                    alert('Please login to save favorites');
                    window.location.href = '/login';
                }
            });
        }
        
        function viewMovie(movieId) {
            alert('Movie details coming soon! ID: ' + movieId);
        }
    </script>
</body>
</html>
'''

LOGIN_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: rgba(255,255,255,0.95);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            width: 100%; 
            max-width: 400px;
            backdrop-filter: blur(10px);
        }
        .logo { 
            text-align: center; 
            font-size: 2.5rem; 
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        h2 {
            text-align: center;
            margin-bottom: 2rem;
            color: #333;
        }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { 
            display: block; 
            margin-bottom: 0.5rem; 
            color: #333; 
            font-weight: 600; 
        }
        .form-group input {
            width: 100%; 
            padding: 1rem; 
            border: 2px solid #e1e5e9; 
            border-radius: 10px;
            font-size: 1rem; 
            transition: all 0.3s ease; 
            outline: none;
        }
        .form-group input:focus { 
            border-color: #667eea; 
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1); 
        }
        .btn {
            width: 100%; 
            padding: 1rem; 
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white; 
            border: none; 
            border-radius: 10px; 
            font-size: 1.1rem;
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s ease;
        }
        .btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 10px 20px rgba(102,126,234,0.3); 
        }
        .links { 
            text-align: center; 
            margin-top: 1.5rem; 
        }
        .links a { 
            color: #667eea; 
            text-decoration: none; 
            font-weight: 600; 
        }
        .flash {
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .flash.danger {
            background: rgba(231,76,60,0.1);
            color: #e74c3c;
            border: 1px solid #e74c3c;
        }
        .flash.success {
            background: rgba(46,204,113,0.1);
            color: #27ae60;
            border: 1px solid #27ae60;
        }
        .demo-credentials {
            background: rgba(102,126,234,0.1);
            padding: 1rem;
            border-radius: 10px;
            margin-top: 1rem;
            text-align: center;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">X★STAR</div>
        <h2>Welcome Back</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
        
        <div class="demo-credentials">
            <strong>Demo Credentials:</strong><br>
            Username: demo | Password: demo123<br>
            Username: admin | Password: admin123
        </div>
        
        <div class="links">
            <p>Don't have an account? <a href="/register">Register here</a></p>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </div>
</body>
</html>
'''

REGISTER_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .register-container {
            background: rgba(255,255,255,0.95);
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            width: 100%; 
            max-width: 400px;
            backdrop-filter: blur(10px);
        }
        .logo { 
            text-align: center; 
            font-size: 2.5rem; 
            background: linear-gradient(45deg, #f093fb, #f5576c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        h2 {
            text-align: center;
            margin-bottom: 2rem;
            color: #333;
        }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { 
            display: block; 
            margin-bottom: 0.5rem; 
            color: #333; 
            font-weight: 600; 
        }
        .form-group input {
            width: 100%; 
            padding: 1rem; 
            border: 2px solid #e1e5e9; 
            border-radius: 10px;
            font-size: 1rem; 
            transition: all 0.3s ease; 
            outline: none;
        }
        .form-group input:focus { 
            border-color: #f5576c; 
            box-shadow: 0 0 0 3px rgba(245,87,108,0.1); 
        }
        .btn {
            width: 100%; 
            padding: 1rem; 
            background: linear-gradient(45deg, #f093fb, #f5576c);
            color: white; 
            border: none; 
            border-radius: 10px; 
            font-size: 1.1rem;
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s ease;
        }
        .btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 10px 20px rgba(245,87,108,0.3); 
        }
        .links { 
            text-align: center; 
            margin-top: 1.5rem; 
        }
        .links a { 
            color: #f5576c; 
            text-decoration: none; 
            font-weight: 600; 
        }
        .flash {
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .flash.danger {
            background: rgba(231,76,60,0.1);
            color: #e74c3c;
            border: 1px solid #e74c3c;
        }
    </style>
</head>
<body>
    <div class="register-container">
        <div class="logo">X★STAR</div>
        <h2>Create Account</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Email (Optional)</label>
                <input type="email" name="email" autocomplete="email">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required autocomplete="new-password" minlength="6">
            </div>
            <button type="submit" class="btn">Register</button>
        </form>
        
        <div class="links">
            <p>Already have an account? <a href="/login">Login here</a></p>
            <p><a href="/">← Back to Home</a></p>
        </div>
    </div>
</body>
</html>
'''

SEARCH_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Results - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header {
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 1rem 0; 
            margin-bottom: 2rem; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo { 
            font-size: 2rem; 
            font-weight: bold; 
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none; 
        }
        .search-box-container { flex: 1; max-width: 500px; margin: 0 2rem; }
        .search-box {
            width: 100%; 
            padding: 0.8rem 1.5rem; 
            border-radius: 25px;
            border: 2px solid rgba(0,212,255,0.3);
            background: rgba(255,255,255,0.1); 
            color: white;
            font-size: 1rem;
        }
        .search-box:focus { 
            outline: none; 
            border-color: #00d4ff;
            background: rgba(255,255,255,0.15); 
        }
        .movies-grid {
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem; 
            margin-top: 2rem;
        }
        .movie-card {
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            overflow: hidden;
            transition: transform 0.3s ease; 
            cursor: pointer;
            padding: 1.5rem;
            text-align: center;
        }
        .movie-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(0,212,255,0.2); 
        }
        .movie-poster {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        .movie-title { 
            font-size: 1.1rem; 
            font-weight: bold; 
            margin-bottom: 0.5rem;
            color: #00d4ff;
        }
        .movie-meta { 
            font-size: 0.9rem; 
            color: #aaa; 
            margin-bottom: 1rem;
        }
        .btn {
            background: rgba(0,212,255,0.2);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(0,212,255,0.4);
        }
        .back-btn {
            display: inline-block;
            margin-top: 2rem;
            color: #00d4ff;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="logo">X★STAR</a>
            <div class="search-box-container">
                <input type="text" class="search-box" placeholder="Search movies..." 
                       value="{{ query }}" id="searchInput">
            </div>
            <div>
                {% if session.user %}
                    <span>👤 {{ session.user }}</span>
                {% else %}
                    <a href="/login" style="color: #00d4ff;">Login</a>
                {% endif %}
            </div>
        </div>
        
        <h1>Search Results for "{{ query }}"</h1>
        
        {% if results %}
            <p>Found {{ results|length }} movies</p>
            <div class="movies-grid">
                {% for movie in results %}
                <div class="movie-card">
                    <div class="movie-poster">{{ movie.poster }}</div>
                    <div class="movie-title">{{ movie.title }}</div>
                    <div class="movie-meta">
                        {{ movie.year }} • ⭐ {{ movie.rating }}
                    </div>
                    <button class="btn" onclick="addToFavorites({{ movie.id }}, '{{ movie.title }}')">
                        💖 Save to Favorites
                    </button>
                </div>
                {% endfor %}
            </div>
        {% else %}
            <p>No results found for "{{ query }}"</p>
        {% endif %}
        
        <a href="/" class="back-btn">← Back to Home</a>
    </div>
    
    <script>
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                window.location.href = '/search?q=' + encodeURIComponent(this.value);
            }
        });
        
        function addToFavorites(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                } else {
                    alert('Please login to save favorites');
                    window.location.href = '/login';
                }
            });
        }
    </script>
</body>
</html>
'''

RECOMMENDATIONS_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recommendations - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header {
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 1rem 0; 
            margin-bottom: 2rem; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo { 
            font-size: 2rem; 
            font-weight: bold; 
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none; 
        }
        h1 {
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .movies-grid {
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem; 
        }
        .movie-card {
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.3s ease; 
            cursor: pointer;
        }
        .movie-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(0,212,255,0.2); 
        }
        .movie-poster { font-size: 3rem; margin-bottom: 1rem; }
        .movie-title { 
            font-size: 1.1rem; 
            font-weight: bold; 
            margin-bottom: 0.5rem;
            color: #00d4ff;
        }
        .btn {
            background: rgba(255,107,157,0.3);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            margin-top: 0.5rem;
        }
        .btn:hover { background: rgba(255,107,157,0.6); }
        .back-btn {
            display: inline-block;
            margin-top: 2rem;
            color: #00d4ff;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="logo">X★STAR</a>
            <div>
                {% if session.user %}
                    <span>👤 {{ session.user }}</span>
                {% else %}
                    <a href="/login" style="color: #00d4ff;">Login</a>
                {% endif %}
            </div>
        </div>
        
        <h1>🎯 AI-Powered Recommendations</h1>
        
        <div class="movies-grid">
            {% for movie in movies %}
            <div class="movie-card">
                <div class="movie-poster">{{ movie.poster }}</div>
                <div class="movie-title">{{ movie.title }}</div>
                <div>{{ movie.year }} • ⭐ {{ movie.rating }}</div>
                <button class="btn" onclick="addToFavorites({{ movie.id }}, '{{ movie.title }}')">
                    💖 Save
                </button>
            </div>
            {% endfor %}
        </div>
        
        <a href="/" class="back-btn">← Back to Home</a>
    </div>
    
    <script>
        function addToFavorites(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                } else {
                    alert('Please login to save favorites');
                    window.location.href = '/login';
                }
            });
        }
    </script>
</body>
</html>
'''

TRENDING_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trending - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header {
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 1rem 0; 
            margin-bottom: 2rem; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo { 
            font-size: 2rem; 
            font-weight: bold; 
            background: linear-gradient(45deg, #ffd93d, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none; 
        }
        h1 {
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #ffd93d, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .movies-grid {
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem; 
        }
        .movie-card {
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.3s ease; 
            cursor: pointer;
        }
        .movie-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(255,217,61,0.2); 
        }
        .movie-poster { font-size: 3rem; margin-bottom: 1rem; }
        .movie-title { 
            font-size: 1.1rem; 
            font-weight: bold; 
            margin-bottom: 0.5rem;
            color: #ffd93d;
        }
        .trending-badge {
            display: inline-block;
            background: linear-gradient(45deg, #ffd93d, #ff6b9d);
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-top: 0.5rem;
            color: #0c0c0c;
            font-weight: bold;
        }
        .btn {
            background: rgba(255,107,157,0.3);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            margin-top: 0.5rem;
        }
        .btn:hover { background: rgba(255,107,157,0.6); }
        .back-btn {
            display: inline-block;
            margin-top: 2rem;
            color: #ffd93d;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="logo">X★STAR</a>
            <div>
                {% if session.user %}
                    <span>👤 {{ session.user }}</span>
                {% else %}
                    <a href="/login" style="color: #ffd93d;">Login</a>
                {% endif %}
            </div>
        </div>
        
        <h1>🔥 Trending Now</h1>
        
        <div class="movies-grid">
            {% for movie in movies %}
            <div class="movie-card">
                <div class="movie-poster">{{ movie.poster }}</div>
                <div class="movie-title">{{ movie.title }}</div>
                <div>{{ movie.year }} • ⭐ {{ movie.rating }}</div>
                <span class="trending-badge">🔥 HOT</span>
                <button class="btn" onclick="addToFavorites({{ movie.id }}, '{{ movie.title }}')">
                    💖 Save
                </button>
            </div>
            {% endfor %}
        </div>
        
        <a href="/" class="back-btn">← Back to Home</a>
    </div>
    
    <script>
        function addToFavorites(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                } else {
                    alert('Please login to save favorites');
                    window.location.href = '/login';
                }
            });
        }
    </script>
</body>
</html>
'''

FAVORITES_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Favorites - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header {
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 1rem 0; 
            margin-bottom: 2rem; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo { 
            font-size: 2rem; 
            font-weight: bold; 
            background: linear-gradient(45deg, #ff6b9d, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none; 
        }
        h1 {
            margin-bottom: 2rem;
            background: linear-gradient(45deg, #ff6b9d, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .movies-grid {
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem; 
        }
        .movie-card {
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.3s ease; 
        }
        .movie-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(255,107,157,0.2); 
        }
        .movie-poster { font-size: 3rem; margin-bottom: 1rem; }
        .movie-title { 
            font-size: 1.1rem; 
            font-weight: bold; 
            margin-bottom: 0.5rem;
            color: #ff6b9d;
        }
        .btn-remove {
            background: rgba(231,76,60,0.3);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            margin-top: 0.5rem;
        }
        .btn-remove:hover { background: rgba(231,76,60,0.6); }
        .back-btn {
            display: inline-block;
            margin-top: 2rem;
            color: #ff6b9d;
            text-decoration: none;
        }
        .empty-state {
            text-align: center;
            padding: 4rem;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="logo">X★STAR</a>
            <div>
                <span>👤 {{ session.user }}</span>
                <a href="/logout" style="color: #ff6b9d; margin-left: 1rem;">Logout</a>
            </div>
        </div>
        
        <h1>⭐ My Favorite Movies</h1>
        
        {% if favorites %}
        <div class="movies-grid">
            {% for fav in favorites %}
            <div class="movie-card">
                <div class="movie-poster">🎬</div>
                <div class="movie-title">{{ fav.title }}</div>
                <div style="font-size: 0.8rem; color: #aaa; margin-top: 0.5rem;">
                    Added: {{ fav.added_at[:10] }}
                </div>
                <button class="btn-remove" onclick="removeFavorite({{ fav.movie_id }}, '{{ fav.title }}')">
                    ❌ Remove
                </button>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h2>No favorites yet! 🎬</h2>
            <p>Start adding movies to your favorites list.</p>
            <a href="/" style="display: inline-block; margin-top: 1rem; color: #ff6b9d;">Browse Movies →</a>
        </div>
        {% endif %}
        
        <a href="/" class="back-btn">← Back to Home</a>
    </div>
    
    <script>
        function removeFavorite(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
'''

ERROR_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error {{ error_code }} - X★STAR</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .error-container { padding: 2rem; }
        .error-code { 
            font-size: 8rem; 
            font-weight: bold; 
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .error-message { font-size: 2rem; margin: 1rem 0; }
        .btn {
            display: inline-block; 
            padding: 1rem 2rem; 
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            color: white; 
            text-decoration: none; 
            border-radius: 10px;
            margin-top: 2rem; 
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{{ error_code }}</div>
        <div class="error-message">{{ error_message }}</div>
        <a href="/" class="btn">Return Home</a>
    </div>
</body>
</html>
'''

# ==================== Run Application ====================
if __name__ == '__main__':
    # Get port from environment variable for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

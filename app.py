# app.py - Complete Movie Recommendation Website with Improvements
import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template_string, request, session, redirect, 
    url_for, flash, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import closing

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-super-secret-key-change-this-in-production'
    DATABASE = 'movies.db'
    TMDB_API_KEY = os.environ.get('TMDB_API_KEY') or ''  # Get from https://www.themoviedb.org/settings/api
    TMDB_BASE_URL = 'https://api.themoviedb.org/3'
    TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    ITEMS_PER_PAGE = 12

app = Flask(__name__)
app.config.from_object(Config)
app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']

# ==================== Database Setup ====================
def init_db():
    """Initialize the database with tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def connect_db():
    """Connect to the database."""
    return sqlite3.connect(app.config['DATABASE'])

def get_db():
    """Get database connection for the current request."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_db()
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at the end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Execute a database query and return results."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute a database modification query."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

# ==================== Authentication Decorator ====================
def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== TMDB API Helper Functions ====================
def tmdb_request(endpoint, params=None):
    """Make a request to TMDB API."""
    if not app.config['TMDB_API_KEY']:
        return None
    
    url = f"{app.config['TMDB_BASE_URL']}{endpoint}"
    default_params = {
        'api_key': app.config['TMDB_API_KEY'],
        'language': 'en-US'
    }
    if params:
        default_params.update(params)
    
    try:
        response = requests.get(url, params=default_params, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        app.logger.error(f"TMDB API error: {e}")
        return None

def get_movie_details(movie_id):
    """Get detailed information about a movie."""
    data = tmdb_request(f'/movie/{movie_id}')
    if data:
        return {
            'id': data.get('id'),
            'title': data.get('title'),
            'overview': data.get('overview'),
            'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{data.get('poster_path')}" if data.get('poster_path') else None,
            'backdrop_path': f"{app.config['TMDB_IMAGE_BASE']}{data.get('backdrop_path')}" if data.get('backdrop_path') else None,
            'release_date': data.get('release_date'),
            'vote_average': data.get('vote_average'),
            'vote_count': data.get('vote_count'),
            'genres': [g['name'] for g in data.get('genres', [])],
            'runtime': data.get('runtime'),
            'tagline': data.get('tagline')
        }
    return None

def search_movies_tmdb(query, page=1):
    """Search for movies using TMDB API."""
    data = tmdb_request('/search/movie', {'query': query, 'page': page})
    if data:
        movies = []
        for movie in data.get('results', []):
            movies.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'overview': movie.get('overview'),
                'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average')
            })
        return {
            'results': movies,
            'total_pages': data.get('total_pages', 1),
            'total_results': data.get('total_results', 0)
        }
    return None

def get_trending_movies(time_window='week', page=1):
    """Get trending movies from TMDB."""
    data = tmdb_request(f'/trending/movie/{time_window}', {'page': page})
    if data:
        movies = []
        for movie in data.get('results', []):
            movies.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'overview': movie.get('overview'),
                'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average')
            })
        return movies
    return []

def get_recommendations_tmdb(movie_id, page=1):
    """Get movie recommendations from TMDB."""
    data = tmdb_request(f'/movie/{movie_id}/recommendations', {'page': page})
    if data:
        movies = []
        for movie in data.get('results', []):
            movies.append({
                'id': movie.get('id'),
                'title': movie.get('title'),
                'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'vote_average': movie.get('vote_average')
            })
        return movies
    return []

def get_popular_movies(page=1):
    """Get popular movies."""
    data = tmdb_request('/movie/popular', {'page': page})
    if data:
        return [{
            'id': m.get('id'),
            'title': m.get('title'),
            'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{m.get('poster_path')}" if m.get('poster_path') else None,
            'vote_average': m.get('vote_average')
        } for m in data.get('results', [])]
    return []

def get_genres():
    """Get list of movie genres."""
    data = tmdb_request('/genre/movie/list')
    if data:
        return data.get('genres', [])
    return []

def discover_movies(genre_id=None, page=1):
    """Discover movies by genre."""
    params = {'page': page, 'sort_by': 'popularity.desc'}
    if genre_id:
        params['with_genres'] = genre_id
    
    data = tmdb_request('/discover/movie', params)
    if data:
        return [{
            'id': m.get('id'),
            'title': m.get('title'),
            'poster_path': f"{app.config['TMDB_IMAGE_BASE']}{m.get('poster_path')}" if m.get('poster_path') else None,
            'vote_average': m.get('vote_average')
        } for m in data.get('results', [])]
    return []

# ==================== AI Recommendation Engine ====================
class MovieRecommender:
    """Simple AI-powered recommendation engine."""
    
    @staticmethod
    def get_personalized_recommendations(user_id, limit=12):
        """Get personalized recommendations based on user's favorites and watch history."""
        # Get user's favorite movies
        favorites = query_db(
            "SELECT movie_id, title FROM favorites WHERE user_id = ? ORDER BY added_at DESC LIMIT 5",
            [user_id]
        )
        
        # Get user's watch history
        watched = query_db(
            "SELECT movie_id, title FROM watch_history WHERE user_id = ? ORDER BY watched_at DESC LIMIT 5",
            [user_id]
        )
        
        recommendations = []
        seen_ids = set()
        
        # If user has favorites, get recommendations based on them
        if favorites:
            for fav in favorites[:3]:  # Use top 3 favorites
                recs = get_recommendations_tmdb(fav['movie_id'])
                if recs:
                    for rec in recs[:4]:  # Get top 4 from each
                        if rec['id'] not in seen_ids:
                            seen_ids.add(rec['id'])
                            recommendations.append(rec)
        
        # Add popular movies if we need more
        if len(recommendations) < limit:
            popular = get_popular_movies()
            if popular:
                for movie in popular:
                    if movie['id'] not in seen_ids and len(recommendations) < limit:
                        seen_ids.add(movie['id'])
                        recommendations.append(movie)
        
        # Add trending movies to fill remaining slots
        if len(recommendations) < limit:
            trending = get_trending_movies()
            for movie in trending:
                if movie['id'] not in seen_ids and len(recommendations) < limit:
                    seen_ids.add(movie['id'])
                    recommendations.append(movie)
        
        return recommendations[:limit]
    
    @staticmethod
    def get_similar_movies(movie_title, limit=6):
        """Get similar movies based on a movie title."""
        # First search for the movie to get its ID
        search_result = search_movies_tmdb(movie_title)
        if search_result and search_result['results']:
            movie_id = search_result['results'][0]['id']
            return get_recommendations_tmdb(movie_id)[:limit]
        return []
    
    @staticmethod
    def get_content_based_recommendations(genres, limit=12):
        """Get recommendations based on preferred genres."""
        if not genres:
            return get_popular_movies(limit)
        
        all_movies = []
        for genre_id in genres[:3]:  # Use top 3 genres
            movies = discover_movies(genre_id)
            all_movies.extend(movies[:limit//3])
        
        return all_movies[:limit]

# ==================== Routes ====================
@app.route('/')
def index():
    """Home page."""
    # Get trending movies for display
    trending = get_trending_movies()[:6]
    popular = get_popular_movies()[:6]
    
    # Get personalized recommendations if logged in
    personalized = []
    favorites_list = []
    if 'user_id' in session:
        personalized = MovieRecommender.get_personalized_recommendations(session['user_id'], 6)
        favorites_list = [f['movie_id'] for f in query_db(
            "SELECT movie_id FROM favorites WHERE user_id = ?", [session['user_id']]
        )]
    
    return render_template_string(MAIN_PAGE_TEMPLATE, 
                                trending=trending,
                                popular=popular,
                                personalized=personalized,
                                favorites_list=favorites_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = query_db(
            "SELECT * FROM users WHERE username = ?", 
            [username], 
            one=True
        )
        
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user'] = user['username']  # For template compatibility
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
        
        # Check if username exists
        existing_user = query_db(
            "SELECT id FROM users WHERE username = ?", 
            [username], 
            one=True
        )
        
        if existing_user:
            flash('Username already exists.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            # Create new user
            user_id = execute_db(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                [username, email, generate_password_hash(password)]
            )
            
            if user_id:
                session.permanent = True
                session['user_id'] = user_id
                session['username'] = username
                session['user'] = username  # For template compatibility
                flash('Account created successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Error creating account.', 'danger')
    
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
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    results = None
    if query:
        results = search_movies_tmdb(query, page)
    
    favorites_list = []
    if 'user_id' in session:
        favorites_list = [f['movie_id'] for f in query_db(
            "SELECT movie_id FROM favorites WHERE user_id = ?", [session['user_id']]
        )]
    
    return render_template_string(SEARCH_PAGE_TEMPLATE,
                                query=query,
                                results=results,
                                page=page,
                                favorites_list=favorites_list)

@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    """Movie details page."""
    movie = get_movie_details(movie_id)
    
    if not movie:
        flash('Movie not found.', 'danger')
        return redirect(url_for('index'))
    
    # Get similar movies
    similar = get_recommendations_tmdb(movie_id)[:6]
    
    # Check if in favorites
    is_favorite = False
    if 'user_id' in session:
        fav = query_db(
            "SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?",
            [session['user_id'], movie_id],
            one=True
        )
        is_favorite = bool(fav)
        
        # Add to watch history
        execute_db(
            """INSERT OR REPLACE INTO watch_history (user_id, movie_id, title, watched_at) 
               VALUES (?, ?, ?, ?)""",
            [session['user_id'], movie_id, movie['title'], datetime.now().isoformat()]
        )
    
    return render_template_string(MOVIE_DETAILS_TEMPLATE,
                                movie=movie,
                                similar=similar,
                                is_favorite=is_favorite)

@app.route('/recommendations')
def recommendations():
    """Recommendations page."""
    page = request.args.get('page', 1, type=int)
    recommendations_list = []
    
    if 'user_id' in session:
        # Get personalized recommendations
        recommendations_list = MovieRecommender.get_personalized_recommendations(
            session['user_id'], 
            app.config['ITEMS_PER_PAGE']
        )
    else:
        # Get popular movies for non-logged in users
        recommendations_list = get_popular_movies(page)
    
    favorites_list = []
    if 'user_id' in session:
        favorites_list = [f['movie_id'] for f in query_db(
            "SELECT movie_id FROM favorites WHERE user_id = ?", [session['user_id']]
        )]
    
    return render_template_string(RECOMMENDATIONS_PAGE_TEMPLATE,
                                movies=recommendations_list,
                                favorites_list=favorites_list)

@app.route('/movies')
def movies():
    """All movies page."""
    page = request.args.get('page', 1, type=int)
    genre_id = request.args.get('genre', type=int)
    
    if genre_id:
        movies_list = discover_movies(genre_id, page)
    else:
        movies_list = get_popular_movies(page)
    
    genres = get_genres()
    
    favorites_list = []
    if 'user_id' in session:
        favorites_list = [f['movie_id'] for f in query_db(
            "SELECT movie_id FROM favorites WHERE user_id = ?", [session['user_id']]
        )]
    
    return render_template_string(MOVIES_PAGE_TEMPLATE,
                                movies=movies_list,
                                genres=genres,
                                selected_genre=genre_id,
                                favorites_list=favorites_list)

@app.route('/genres')
def genres():
    """Genres page."""
    genres_list = get_genres()
    return render_template_string(GENRES_PAGE_TEMPLATE, genres=genres_list)

@app.route('/trending')
def trending():
    """Trending page."""
    time_window = request.args.get('window', 'week')
    page = request.args.get('page', 1, type=int)
    
    trending_movies = get_trending_movies(time_window, page)
    
    favorites_list = []
    if 'user_id' in session:
        favorites_list = [f['movie_id'] for f in query_db(
            "SELECT movie_id FROM favorites WHERE user_id = ?", [session['user_id']]
        )]
    
    return render_template_string(TRENDING_PAGE_TEMPLATE,
                                movies=trending_movies,
                                time_window=time_window,
                                favorites_list=favorites_list)

@app.route('/favorites')
@login_required
def favorites():
    """User favorites page."""
    user_favorites = query_db(
        """SELECT f.*, f.added_at as added 
           FROM favorites f 
           WHERE f.user_id = ? 
           ORDER BY f.added_at DESC""",
        [session['user_id']]
    )
    
    # Fetch movie details for each favorite
    favorites_with_details = []
    for fav in user_favorites:
        details = get_movie_details(fav['movie_id'])
        if details:
            details['added_at'] = fav['added']
            favorites_with_details.append(details)
    
    return render_template_string(FAVORITES_PAGE_TEMPLATE,
                                favorites=favorites_with_details)

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    """Add movie to favorites."""
    data = request.get_json()
    movie_title = data.get('movie')
    movie_id = data.get('movie_id')
    
    if not movie_id and movie_title:
        # Search for movie to get ID
        search_result = search_movies_tmdb(movie_title)
        if search_result and search_result['results']:
            movie_id = search_result['results'][0]['id']
            movie_title = search_result['results'][0]['title']
    
    if movie_id and movie_title:
        # Check if already in favorites
        existing = query_db(
            "SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?",
            [session['user_id'], movie_id],
            one=True
        )
        
        if existing:
            # Remove from favorites
            execute_db(
                "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
                [session['user_id'], movie_id]
            )
            return jsonify({'success': True, 'message': f'Removed from favorites!', 'action': 'removed'})
        else:
            # Add to favorites
            execute_db(
                "INSERT INTO favorites (user_id, movie_id, title) VALUES (?, ?, ?)",
                [session['user_id'], movie_id, movie_title]
            )
            return jsonify({'success': True, 'message': f'Added to favorites!', 'action': 'added'})
    
    return jsonify({'success': False, 'message': 'Movie not found.'}), 400

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    user = query_db(
        "SELECT * FROM users WHERE id = ?",
        [session['user_id']],
        one=True
    )
    
    # Get user stats
    favorites_count = query_db(
        "SELECT COUNT(*) as count FROM favorites WHERE user_id = ?",
        [session['user_id']],
        one=True
    )['count']
    
    watched_count = query_db(
        "SELECT COUNT(DISTINCT movie_id) as count FROM watch_history WHERE user_id = ?",
        [session['user_id']],
        one=True
    )['count']
    
    # Get recently watched
    recent_watched = query_db(
        "SELECT * FROM watch_history WHERE user_id = ? ORDER BY watched_at DESC LIMIT 10",
        [session['user_id']]
    )
    
    return render_template_string(PROFILE_PAGE_TEMPLATE,
                                user=user,
                                favorites_count=favorites_count,
                                watched_count=watched_count,
                                recent_watched=recent_watched)

@app.route('/api/recommendations/<int:movie_id>')
def api_recommendations(movie_id):
    """API endpoint for movie recommendations."""
    recommendations = get_recommendations_tmdb(movie_id)
    return jsonify(recommendations)

@app.route('/api/trending')
def api_trending():
    """API endpoint for trending movies."""
    window = request.args.get('window', 'week')
    movies = get_trending_movies(window)
    return jsonify(movies)

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
# (Previous MAIN_PAGE_TEMPLATE, LOGIN_PAGE_TEMPLATE, REGISTER_PAGE_TEMPLATE remain the same)
# Adding new templates for the new routes

SEARCH_PAGE_TEMPLATE = """
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
            display: flex; justify-content: space-between; align-items: center;
            padding: 1rem 0; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo { font-size: 2rem; font-weight: bold; color: #00d4ff; text-decoration: none; }
        .search-box-container { flex: 1; max-width: 500px; margin: 0 2rem; }
        .search-box {
            width: 100%; padding: 0.8rem 1.5rem; border-radius: 25px;
            border: none; background: rgba(255,255,255,0.1); color: white;
            font-size: 1rem;
        }
        .search-box:focus { outline: 2px solid #00d4ff; background: rgba(255,255,255,0.15); }
        .movies-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem; margin-top: 2rem;
        }
        .movie-card {
            background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden;
            transition: transform 0.3s ease; cursor: pointer;
        }
        .movie-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,212,255,0.2); }
        .movie-poster {
            width: 100%; height: 300px; object-fit: cover;
            background: linear-gradient(45deg, #1a1a2e, #16213e);
        }
        .movie-info { padding: 1rem; }
        .movie-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem; }
        .movie-meta { font-size: 0.9rem; color: #aaa; display: flex; justify-content: space-between; }
        .pagination { display: flex; justify-content: center; gap: 0.5rem; margin-top: 2rem; }
        .page-link {
            padding: 0.5rem 1rem; background: rgba(255,255,255,0.1);
            color: white; text-decoration: none; border-radius: 5px;
        }
        .page-link:hover { background: #00d4ff; color: #0c0c0c; }
        .favorite-btn {
            background: none; border: none; color: #ff6b9d; cursor: pointer;
            font-size: 1.2rem; padding: 0.2rem 0.5rem;
        }
        .favorite-btn.active { color: #ffd93d; }
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
                    <a href="/favorites" style="color: #00d4ff; margin-right: 1rem;">⭐ Favorites</a>
                    <a href="/profile" style="color: white;">👤 {{ session.user }}</a>
                {% else %}
                    <a href="/login" style="color: #00d4ff;">Login</a>
                {% endif %}
            </div>
        </div>
        
        <h1>Search Results for "{{ query }}"</h1>
        
        {% if results and results.results %}
            <p>Found {{ results.total_results }} movies</p>
            <div class="movies-grid">
                {% for movie in results.results %}
                <div class="movie-card" onclick="location.href='/movie/{{ movie.id }}'">
                    {% if movie.poster_path %}
                    <img src="{{ movie.poster_path }}" alt="{{ movie.title }}" class="movie-poster">
                    {% else %}
                    <div class="movie-poster" style="display: flex; align-items: center; justify-content: center;">
                        🎬 No Image
                    </div>
                    {% endif %}
                    <div class="movie-info">
                        <div class="movie-title">{{ movie.title }}</div>
                        <div class="movie-meta">
                            <span>⭐ {{ "%.1f"|format(movie.vote_average) if movie.vote_average else 'N/A' }}</span>
                            <span>{{ movie.release_date[:4] if movie.release_date else 'N/A' }}</span>
                        </div>
                        <button class="favorite-btn {% if movie.id in favorites_list %}active{% endif %}" 
                                onclick="event.stopPropagation(); toggleFavorite({{ movie.id }}, '{{ movie.title }}')">
                            {% if movie.id in favorites_list %}❤️{% else %}🤍{% endif %}
                        </button>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            {% if results.total_pages > 1 %}
            <div class="pagination">
                {% for p in range(1, min(results.total_pages, 10) + 1) %}
                <a href="?q={{ query }}&page={{ p }}" class="page-link">{{ p }}</a>
                {% endfor %}
            </div>
            {% endif %}
        {% else %}
            <p>No results found for "{{ query }}"</p>
        {% endif %}
    </div>
    
    <script>
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                window.location.href = '/search?q=' + encodeURIComponent(this.value);
            }
        });
        
        function toggleFavorite(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
"""

MOVIE_DETAILS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ movie.title }} - X★STAR</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .backdrop {
            position: relative; height: 500px; overflow: hidden;
        }
        .backdrop-image {
            width: 100%; height: 100%; object-fit: cover; opacity: 0.4;
        }
        .backdrop-overlay {
            position: absolute; bottom: 0; left: 0; right: 0;
            background: linear-gradient(transparent, #0c0c0c);
            padding: 4rem 2rem 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
        .movie-header {
            display: flex; gap: 2rem; margin-top: -150px; position: relative;
        }
        .poster {
            width: 300px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }
        .movie-info { flex: 1; padding-top: 2rem; }
        .movie-title { font-size: 3rem; margin-bottom: 1rem; }
        .movie-meta { display: flex; gap: 2rem; margin-bottom: 1.5rem; color: #ccc; }
        .genres { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
        .genre-tag {
            background: rgba(0,212,255,0.2); padding: 0.5rem 1rem;
            border-radius: 20px; font-size: 0.9rem;
        }
        .overview { font-size: 1.1rem; line-height: 1.8; margin-bottom: 2rem; opacity: 0.9; }
        .actions { display: flex; gap: 1rem; }
        .btn {
            padding: 1rem 2rem; border-radius: 10px; text-decoration: none;
            font-weight: bold; transition: all 0.3s ease; border: none; cursor: pointer;
            font-size: 1rem;
        }
        .btn-primary {
            background: linear-gradient(45deg, #00d4ff, #ff6b9d);
            color: white;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0,212,255,0.3); }
        .btn-secondary {
            background: rgba(255,255,255,0.1); color: white;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.2); }
        .section { margin: 3rem 0; }
        .section-title { font-size: 2rem; margin-bottom: 1.5rem; color: #00d4ff; }
        .similar-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 1.5rem;
        }
        .similar-card {
            background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden;
            cursor: pointer; transition: transform 0.3s ease;
        }
        .similar-card:hover { transform: translateY(-5px); }
        .similar-poster {
            width: 100%; height: 250px; object-fit: cover;
        }
        .similar-title { padding: 1rem; font-size: 1rem; }
        
        @media (max-width: 768px) {
            .movie-header { flex-direction: column; align-items: center; }
            .poster { width: 200px; }
            .movie-title { font-size: 2rem; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="backdrop">
        {% if movie.backdrop_path %}
        <img src="{{ movie.backdrop_path }}" alt="{{ movie.title }}" class="backdrop-image">
        {% else %}
        <div class="backdrop-image" style="background: linear-gradient(45deg, #1a1a2e, #16213e);"></div>
        {% endif %}
        <div class="backdrop-overlay">
            <div class="container">
                <a href="/" style="color: white; text-decoration: none;">← Back</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="movie-header">
            {% if movie.poster_path %}
            <img src="{{ movie.poster_path }}" alt="{{ movie.title }}" class="poster">
            {% else %}
            <div class="poster" style="background: linear-gradient(45deg, #1a1a2e, #16213e); height: 450px; display: flex; align-items: center; justify-content: center;">
                🎬 No Poster
            </div>
            {% endif %}
            
            <div class="movie-info">
                <h1 class="movie-title">{{ movie.title }}</h1>
                {% if movie.tagline %}
                <p style="font-style: italic; margin-bottom: 1rem; opacity: 0.8;">"{{ movie.tagline }}"</p>
                {% endif %}
                
                <div class="movie-meta">
                    <span>⭐ {{ "%.1f"|format(movie.vote_average) if movie.vote_average else 'N/A' }}/10</span>
                    <span>🗳️ {{ movie.vote_count }} votes</span>
                    <span>📅 {{ movie.release_date[:4] if movie.release_date else 'N/A' }}</span>
                    <span>⏱️ {{ movie.runtime }} min</span>
                </div>
                
                <div class="genres">
                    {% for genre in movie.genres %}
                    <span class="genre-tag">{{ genre }}</span>
                    {% endfor %}
                </div>
                
                <p class="overview">{{ movie.overview }}</p>
                
                <div class="actions">
                    <button class="btn btn-primary" onclick="toggleFavorite({{ movie.id }}, '{{ movie.title }}')">
                        {% if is_favorite %}❤️ Remove from Favorites{% else %}🤍 Add to Favorites{% endif %}
                    </button>
                    <a href="/recommendations" class="btn btn-secondary">🎯 Get Similar Movies</a>
                </div>
            </div>
        </div>
        
        {% if similar %}
        <div class="section">
            <h2 class="section-title">Similar Movies You Might Like</h2>
            <div class="similar-grid">
                {% for movie in similar %}
                <div class="similar-card" onclick="location.href='/movie/{{ movie.id }}'">
                    {% if movie.poster_path %}
                    <img src="{{ movie.poster_path }}" alt="{{ movie.title }}" class="similar-poster">
                    {% else %}
                    <div class="similar-poster" style="display: flex; align-items: center; justify-content: center;">
                        🎬
                    </div>
                    {% endif %}
                    <div class="similar-title">
                        {{ movie.title }}
                        <span style="display: block; font-size: 0.9rem; color: #ffd93d;">
                            ⭐ {{ "%.1f"|format(movie.vote_average) if movie.vote_average else 'N/A' }}
                        </span>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <script>
        function toggleFavorite(movieId, movieTitle) {
            fetch('/add_favorite', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({movie_id: movieId, movie: movieTitle})
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
"""

# Additional templates (RECOMMENDATIONS_PAGE_TEMPLATE, MOVIES_PAGE_TEMPLATE, etc.) 
# would follow the same pattern as above

ERROR_PAGE_TEMPLATE = """
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
        .error-code { font-size: 8rem; font-weight: bold; color: #00d4ff; }
        .error-message { font-size: 2rem; margin: 1rem 0; }
        .btn {
            display: inline-block; padding: 1rem 2rem; background: #00d4ff;
            color: #0c0c0c; text-decoration: none; border-radius: 10px;
            margin-top: 2rem; font-weight: bold;
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
"""

# ==================== Schema Definition ====================
SCHEMA_SQL = """
-- schema.sql
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

DROP TABLE IF EXISTS favorites;
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, movie_id)
);

DROP TABLE IF EXISTS watch_history;
CREATE TABLE watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, movie_id, watched_at)
);

DROP TABLE IF EXISTS ratings;
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, movie_id)
);

CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_watch_history_user ON watch_history(user_id);
CREATE INDEX idx_ratings_user ON ratings(user_id);
"""

# Write schema to file
with open('schema.sql', 'w') as f:
    f.write(SCHEMA_SQL)

# ==================== Application Startup ====================
def initialize_app():
    """Initialize the application."""
    # Create database if it doesn't exist
    if not os.path.exists(app.config['DATABASE']):
        init_db()
        print("Database initialized.")
    
    # Check for TMDB API key
    if not app.config['TMDB_API_KEY']:
        print("Warning: TMDB_API_KEY not set. Real movie data won't be available.")
        print("Get your free API key at: https://www.themoviedb.org/settings/api")

if __name__ == '__main__':
    initialize_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

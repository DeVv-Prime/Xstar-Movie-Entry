-- schema.sql - Database initialization
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
    poster_path TEXT,
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
    review TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, movie_id)
);

DROP TABLE IF EXISTS user_preferences;
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    favorite_genres TEXT,
    notification_enabled BOOLEAN DEFAULT 1,
    theme TEXT DEFAULT 'dark',
    language TEXT DEFAULT 'en',
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Indexes for better performance
CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_movie ON favorites(movie_id);
CREATE INDEX idx_watch_history_user ON watch_history(user_id);
CREATE INDEX idx_ratings_user ON ratings(user_id);
CREATE INDEX idx_ratings_movie ON ratings(movie_id);

-- Insert default admin user
INSERT OR IGNORE INTO users (username, email, password_hash) 
VALUES ('admin', 'admin@xstar.com', 'pbkdf2:sha256:600000$default$daf992b00b18b181d8220a9b1e8c2b6b9c3e8d2d7e8c9f0a1b2c3d4e5f6a7b8c');

-- Insert sample data for demo
INSERT OR IGNORE INTO users (username, email, password_hash) 
VALUES ('demo', 'demo@xstar.com', 'pbkdf2:sha256:600000$default$daf992b00b18b181d8220a9b1e8c2b6b9c3e8d2d7e8c9f0a1b2c3d4e5f6a7b8c');

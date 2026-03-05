from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = 'data/caddymate_store.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return send_from_directory('.', 'home.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('.', path)

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)

@app.route('/api/items/<int:category_id>')
def get_items_by_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE category_id = ? ORDER BY name', (category_id,))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

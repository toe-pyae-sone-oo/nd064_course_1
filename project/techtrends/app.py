import sqlite3

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

import threading
import logging
from flask.logging import default_handler

lock = threading.Lock()
total_connections = 0

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    global total_connections
    with lock:
        total_connections += 1
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Function to get the total number of posts in database
def get_post_count():
    connection = get_db_connection()
    post_count = connection.execute('SELECT COUNT(id) FROM posts').fetchone()
    return post_count[0]

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.info('Article not found!')
        return render_template('404.html'), 404
    else:
        app.logger.info('Article "{}" retrieved!'.format(post['title']))
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('About Us retrieved!')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.info('New article "{}" is created!'.format(title))

            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/healthz')
def status():
    response = app.response_class(
        response=json.dumps({"result": "OK - healthy"}),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/metrics')
def metrics():
    post_count = get_post_count()
    response = app.response_class(
        response=json.dumps({
            "db_connection_count": total_connections,
            "post_count": post_count,
        }),
        status=200,
        mimetype='application/json'
    )
    return response

class AppFormatter(logging.Formatter):
    def format(self, record):
        return super().format(record)

# start the application on port 3111
if __name__ == "__main__":
    default_handler.setFormatter(AppFormatter(fmt='%(levelname)s:%(name)s:%(asctime)s, %(message)s', datefmt='%d/%m/%Y, %H:%M:%S'))
    app.logger.propagate = False

    logging.basicConfig(
        level=logging.DEBUG,
    )

    app.run(host='0.0.0.0', port='3111')

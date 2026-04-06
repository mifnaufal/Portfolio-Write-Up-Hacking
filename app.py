import sqlite3
from flask import Flask, g
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db: db.close()

@app.cli.command('init-db')
def init_db():
    with app.open_resource('schema.sql') as f:
        get_db().executescript(f.read().decode('utf8'))
    print('✅ DB initialized.')

@app.route('/')
def index():
    return 'Portfolio Ready'

if __name__ == '__main__':
    app.run(debug=True)
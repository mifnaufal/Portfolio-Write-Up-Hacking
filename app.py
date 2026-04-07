import os, re, sqlite3, click, bcrypt, markdown
from functools import wraps
from flask import Flask, g, request, session, redirect, url_for, flash, render_template, abort
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField, SelectMultipleField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

# ──────────────────────────────────────────────────────────────
# DB & UTILS
# ──────────────────────────────────────────────────────────────
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

def generate_slug(text, table='categories'):
    base = re.sub(r'[^a-z0-9]+', '-', text.lower().strip()).strip('-')
    slug, counter = base, 2
    while get_db().execute(f'SELECT 1 FROM {table} WHERE slug=?', (slug,)).fetchone():
        slug = f"{base}-{counter}"; counter += 1
    return slug

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Silakan login.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.cli.command('init-db')
def init_db():
    with app.open_resource('schema.sql') as f:
        get_db().executescript(f.read().decode('utf8'))
    print('✅ DB initialized.')

@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin(username, password):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        get_db().execute('INSERT INTO admin (username, password_hash) VALUES (?, ?)', (username, pw_hash))
        print(f'✅ Admin {username} created.')
    except Exception as e: print(f'❌ {e}')

# ──────────────────────────────────────────────────────────────
# FORMS
# ──────────────────────────────────────────────────────────────
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CategoryForm(FlaskForm):
    name = StringField('Nama Kategori', validators=[DataRequired()])
    submit = SubmitField('Simpan')

class WriteupForm(FlaskForm):
    title = StringField('Judul', validators=[DataRequired()])
    content_md = TextAreaField('Konten Markdown', validators=[DataRequired()])
    categories = SelectMultipleField('Kategori', coerce=int, validators=[DataRequired()])
    is_published = BooleanField('Publish')
    submit = SubmitField('Simpan')

# ──────────────────────────────────────────────────────────────
# PUBLIC ROUTES
# ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    data = db.execute("""
        SELECT w.id, w.title, w.slug, w.created_at, GROUP_CONCAT(c.name) as cats
        FROM writeups w LEFT JOIN writeup_categories wc ON w.id = wc.writeup_id
        LEFT JOIN categories c ON wc.category_id = c.id
        WHERE w.is_published=1 GROUP BY w.id ORDER BY w.created_at DESC
    """).fetchall()
    return render_template('index.html', writeups=data)

@app.route('/category/<slug>')
def category(slug):
    db = get_db()
    cat = db.execute('SELECT * FROM categories WHERE slug=?', (slug,)).fetchone()
    if not cat: abort(404)
    data = db.execute("""
        SELECT w.id, w.title, w.slug, w.created_at, GROUP_CONCAT(c.name) as cats
        FROM writeups w JOIN writeup_categories wc ON w.id = wc.writeup_id
        JOIN categories c ON wc.category_id = c.id
        WHERE w.is_published=1 AND wc.category_id=? GROUP BY w.id ORDER BY w.created_at DESC
    """, (cat['id'],)).fetchall()
    return render_template('category.html', category=cat, writeups=data)

@app.route('/w/<slug>')
def writeup_detail(slug):
    db = get_db()
    wu = db.execute('SELECT * FROM writeups WHERE slug=? AND is_published=1', (slug,)).fetchone()
    if not wu: abort(404)
    cats = db.execute("SELECT c.name FROM categories c JOIN writeup_categories wc ON c.id = wc.category_id WHERE wc.writeup_id=?", (wu['id'],)).fetchall()
    html = markdown.markdown(wu['content_md'], extensions=['fenced_code', 'codehilite'])
    return render_template('writeup.html', writeup=wu, categories=[c['name'] for c in cats], html_content=html)

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q: return redirect(url_for('index'))
    db = get_db()
    data = db.execute("""
        SELECT w.id, w.title, w.slug, w.created_at, GROUP_CONCAT(c.name) as cats
        FROM writeups w LEFT JOIN writeup_categories wc ON w.id = wc.writeup_id
        LEFT JOIN categories c ON wc.category_id = c.id
        WHERE w.is_published=1 AND (w.title LIKE ? OR w.content_md LIKE ?)
        GROUP BY w.id ORDER BY w.created_at DESC
    """, (f'%{q}%', f'%{q}%')).fetchall()
    return render_template('search.html', results=data, query=q)

# ──────────────────────────────────────────────────────────────
# ADMIN AUTH
# ──────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        user = db.execute('SELECT * FROM admin WHERE username=?', (form.username.data,)).fetchone()
        if user and bcrypt.checkpw(form.password.data.encode(), user['password_hash'].encode()):
            session.clear()
            session['admin_id'] = user['id']
            return redirect(url_for('admin_writeups'))
        flash('Username/password salah.', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ──────────────────────────────────────────────────────────────
# ADMIN CRUD
# ──────────────────────────────────────────────────────────────
def get_cat_choices():
    return [(c['id'], c['name']) for c in get_db().execute('SELECT id, name FROM categories ORDER BY name').fetchall()]

@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    db = get_db()
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            db.execute('INSERT INTO categories (name, slug) VALUES (?, ?)',
                       (form.name.data, generate_slug(form.name.data, 'categories')))
            db.commit(); flash('✅ Kategori ditambahkan.', 'success')
        except sqlite3.IntegrityError: flash('❌ Nama sudah ada.', 'error')
        return redirect(url_for('admin_categories'))
    return render_template('admin/categories.html', form=form, categories=db.execute('SELECT * FROM categories ORDER BY name').fetchall())

@app.route('/admin/categories/<int:id>/edit', methods=['POST'])
@login_required
def admin_cat_edit(id):
    name = request.form.get('name', '').strip()
    if name:
        get_db().execute('UPDATE categories SET name=?, slug=? WHERE id=?', (name, generate_slug(name, 'categories'), id))
        get_db().commit()
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:id>/delete', methods=['POST'])
@login_required
def admin_cat_delete(id):
    get_db().execute('DELETE FROM categories WHERE id=?', (id,))
    get_db().commit()
    return redirect(url_for('admin_categories'))

@app.route('/admin/writeups', methods=['GET', 'POST'])
@login_required
def admin_writeups():
    db = get_db()
    form = WriteupForm()
    form.categories.choices = get_cat_choices()
    if form.validate_on_submit():
        slug = generate_slug(form.title.data, 'writeups')
        db.execute('INSERT INTO writeups (title, slug, content_md, is_published) VALUES (?,?,?,?)',
                   (form.title.data, slug, form.content_md.data, form.is_published.data))
        wu_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        for cid in form.categories.data:
            db.execute('INSERT OR IGNORE INTO writeup_categories VALUES (?,?)', (wu_id, cid))
        db.commit(); flash('✅ Write-up dibuat.', 'success')
        return redirect(url_for('admin_writeups'))
    return render_template('admin/writeups.html', form=form, writeups=db.execute('SELECT * FROM writeups ORDER BY created_at DESC').fetchall())

@app.route('/admin/writeups/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_wu_edit(id):
    db = get_db()
    wu = db.execute('SELECT * FROM writeups WHERE id=?', (id,)).fetchone()
    if not wu: abort(404)
    form = WriteupForm(obj=wu)
    form.categories.choices = get_cat_choices()
    if form.validate_on_submit():
        db.execute('UPDATE writeups SET title=?, slug=?, content_md=?, is_published=? WHERE id=?',
                   (form.title.data, generate_slug(form.title.data, 'writeups'), form.content_md.data, form.is_published.data, id))
        # 🔁 Sync Junction
        db.execute('DELETE FROM writeup_categories WHERE writeup_id=?', (id,))
        for cid in form.categories.data:
            db.execute('INSERT OR IGNORE INTO writeup_categories VALUES (?,?)', (id, cid))
        db.commit(); flash('✅ Write-up diperbarui.', 'success')
        return redirect(url_for('admin_writeups'))
    form.categories.data = [r['category_id'] for r in db.execute('SELECT category_id FROM writeup_categories WHERE writeup_id=?', (id,)).fetchall()]
    return render_template('admin/writeup_edit.html', form=form, writeup=wu)

@app.route('/admin/writeups/<int:id>/delete', methods=['POST'])
@login_required
def admin_wu_delete(id):
    get_db().execute('DELETE FROM writeups WHERE id=?', (id,))
    get_db().commit()
    return redirect(url_for('admin_writeups'))

@app.errorhandler(404)
def not_found(e): return "404 Not Found", 404

if __name__ == '__main__':
    app.run(debug=True)
import os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE=os.path.dirname(os.path.abspath(__file__))
app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY') or secrets.token_hex(32)
DB_PATH=os.environ.get('DATABASE_PATH',os.path.join(BASE,'dbit_fest.db'))

def db():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con

def init_db():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','student')));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,people INTEGER,time TEXT NOT NULL,duration REAL,cost REAL,priority TEXT,notes TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,category TEXT,people INTEGER,time TEXT,notes TEXT,status TEXT DEFAULT 'Pending',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(user_id) REFERENCES users(id));''')
        if not c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone():
            username=os.environ.get('ADMIN_USERNAME','admin'); password=os.environ.get('ADMIN_PASSWORD','ChangeMe123!')
            c.execute('INSERT INTO users(username,full_name,password_hash,role) VALUES(?,?,?,?)',(username,'Fest Administrator',generate_password_hash(password),'admin'))
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('budget','100000')")
init_db()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if 'user_id' not in session: return redirect(url_for('home'))
        return fn(*a,**kw)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if 'user_id' not in session: return jsonify(error='Sign in required'),401
        if session.get('role')!='admin': return jsonify(error='Admin access required'),403
        return fn(*a,**kw)
    return wrapped

def csrf_ok():
    token=request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
    return bool(token and secrets.compare_digest(token,session.get('csrf_token','')))

@app.before_request
def protect_posts():
    if request.method=='POST' and request.endpoint in {'login','register'}:
        if not csrf_ok(): abort(400)

@app.route('/')
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    session.setdefault('csrf_token',secrets.token_urlsafe(24))
    return render_template('auth.html',csrf_token=session['csrf_token'])

@app.post('/login')
def login():
    username=request.form.get('username','').strip().lower(); password=request.form.get('password','')
    with db() as c: u=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    if not u or not check_password_hash(u['password_hash'],password):
        flash('Invalid username or password.'); return redirect(url_for('home'))
    session.clear(); session.update(user_id=u['id'],username=u['username'],full_name=u['full_name'],role=u['role'],csrf_token=secrets.token_urlsafe(24))
    return redirect(url_for('dashboard'))

@app.post('/register')
def register():
    username=request.form.get('username','').strip().lower(); full_name=request.form.get('full_name','').strip(); password=request.form.get('password','')
    if len(username)<3 or len(password)<8 or not full_name:
        flash('Enter a name, username (3+ characters), and password (8+ characters).'); return redirect(url_for('home'))
    try:
        with db() as c: c.execute('INSERT INTO users(username,full_name,password_hash,role) VALUES(?,?,?,?)',(username,full_name,generate_password_hash(password),'student'))
    except sqlite3.IntegrityError:
        flash('That username is already taken.'); return redirect(url_for('home'))
    flash('Student account created. Please sign in.'); return redirect(url_for('home'))

@app.get('/dashboard')
@login_required
def dashboard(): return render_template('index.html',current_user=session)

@app.get('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.get('/api/bootstrap')
@login_required
def bootstrap():
    with db() as c:
        events=[dict(x) for x in c.execute('SELECT * FROM events ORDER BY time,id').fetchall()]
        budget=c.execute("SELECT value FROM settings WHERE key='budget'").fetchone()['value']
    return jsonify(events=events,budget=budget,role=session['role'],csrf=session['csrf_token'])

@app.post('/api/events')
@admin_required
def add_event():
    if not csrf_ok(): return jsonify(error='Security token expired. Refresh the page.'),400
    d=request.get_json(force=True); required=['name','category','time']
    if any(not str(d.get(k,'')).strip() for k in required): return jsonify(error='Name, category and time are required.'),400
    with db() as c:
        cur=c.execute('INSERT INTO events(name,category,people,time,duration,cost,priority,notes) VALUES(?,?,?,?,?,?,?,?)',(d['name'].strip(),d['category'],int(d.get('people',0)),d['time'],float(d.get('duration',1)),float(d.get('cost',0)),d.get('priority','Standard'),d.get('notes','')))
        row=c.execute('SELECT * FROM events WHERE id=?',(cur.lastrowid,)).fetchone()
    return jsonify(event=dict(row)),201

@app.delete('/api/events/<int:event_id>')
@admin_required
def delete_event(event_id):
    if not csrf_ok(): return jsonify(error='Security token expired.'),400
    with db() as c: c.execute('DELETE FROM events WHERE id=?',(event_id,))
    return jsonify(ok=True)

@app.put('/api/budget')
@admin_required
def set_budget():
    if not csrf_ok(): return jsonify(error='Security token expired.'),400
    value=str(max(0,float(request.get_json(force=True).get('budget',0))))
    with db() as c: c.execute("INSERT INTO settings(key,value) VALUES('budget',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(value,))
    return jsonify(budget=value)

@app.get('/api/requests')
@login_required
def list_requests():
    with db() as c:
        if session['role']=='admin': rows=c.execute('SELECT r.*,u.username,u.full_name FROM requests r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC').fetchall()
        else: rows=c.execute('SELECT * FROM requests WHERE user_id=? ORDER BY id DESC',(session['user_id'],)).fetchall()
    return jsonify(requests=[dict(r) for r in rows])

@app.post('/api/requests')
@login_required
def create_request():
    if not csrf_ok(): return jsonify(error='Security token expired.'),400
    d=request.get_json(force=True)
    if not str(d.get('name','')).strip(): return jsonify(error='Activity name is required.'),400
    with db() as c: c.execute('INSERT INTO requests(user_id,name,category,people,time,notes) VALUES(?,?,?,?,?,?)',(session['user_id'],d['name'].strip(),d.get('category',''),int(d.get('people',0)),d.get('time',''),d.get('notes','')))
    return jsonify(ok=True),201

@app.patch('/api/requests/<int:req_id>')
@admin_required
def update_request(req_id):
    if not csrf_ok(): return jsonify(error='Security token expired.'),400
    status=request.get_json(force=True).get('status')
    if status not in ('Approved','Rejected','Pending'): return jsonify(error='Invalid status.'),400
    with db() as c: c.execute('UPDATE requests SET status=? WHERE id=?',(status,req_id))
    return jsonify(ok=True)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=os.environ.get('FLASK_DEBUG')=='1')

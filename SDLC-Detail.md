**SDLC Detail: Portfolio Write-Up Hacking (Flask + SQLite + Kategori Dinamis + Markdown) – Proxmox Edition**

**1. Perencanaan**
- **Tujuan:** Portfolio ringan, fokus write-up hacking, kategori fleksibel (many-to-many), render Markdown aman.
- **Stack:** Python 3.10+, Flask, `sqlite3` (bawaan), `markdown`, `Pygments`, `bcrypt`, `Flask-WTF`, Gunicorn, Nginx.
- **Fitur MVP:** 
  - Public: List, filter `/category/<slug>`, detail `/w/<slug>`, pencarian, kode syntax highlight.
  - Admin: Login, CRUD kategori, CRUD write-up (Markdown), multi-kategori assignment, toggle publish.
- **Timeline:** 10–14 hari.
- **Tools:** Git, VS Code, SQLite CLI, Proxmox VE.

**2. Analisis Kebutuhan**
- **Fungsional:** Admin buat/edit/hapus kategori (auto-slug). Admin pilih ≥1 kategori per write-up. Konten murni Markdown → HTML. Filter & pencarian realtime.
- **Non-Fungsional:** Responsif, load <1s, SQLite `chmod 600`, anti-SQLi/XSS/CSRF, session `secure/httponly`, backup otomatis (Proxmox + cron).
- **Batasan:** Monolith ringan, 1 admin, query manual terstruktur, tanpa ORM, DB terpisah dari folder publik.

**3. Desain**
- **Struktur Folder:**
  ```
  project/
  ├── app.py
  ├── config.py
  ├── requirements.txt
  ├── data/portfolio.db   ← di luar root web
  ├── templates/ (base, index, writeup, admin/)
  └── static/ (css, pygments.css)
  ```
- **Skema SQLite:**
  - `categories`: `id PK, name UNIQUE, slug UNIQUE, created_at`
  - `writeups`: `id PK, title, slug UNIQUE, content_md, is_published BOOL, created_at`
  - `writeup_categories`: `writeup_id INTEGER, category_id INTEGER, PK(writeup_id, category_id), FKs CASCADE`
  - `admin`: `id PK, username UNIQUE, password_hash`
- **Keamanan Desain:** `PRAGMA foreign_keys=ON` per koneksi, prepared statements wajib, bcrypt, CSRF token, `.db` di-block Nginx, session cookie flags aktif.
- **UI Flow:** Form kategori (input nama → auto-slug). Form write-up (judul, textarea Markdown, checkbox multi-kategori, toggle publish). Preview opsional via JS.

**4. Implementasi**
- Setup: `python3 -m venv venv` → `source venv/bin/activate` → `pip install flask markdown pygments bcrypt gunicorn Flask-WTF`
- **Backend (`app.py`):**
  - Init DB: enable FK, create tables + indeks.
  - Route Admin: `/admin/login`, `/admin/categories` (CRUD), `/admin/writeups` (CRUD + junction logic: `DELETE` lama → `INSERT` baru).
  - Route Public: `/`, `/category/<slug>`, `/w/<slug>`, `/search?q=`.
  - Query: selalu `?` placeholder. Join 3 tabel untuk filter kategori.
  - Render: `markdown.markdown(text, extensions=['fenced_code', 'codehilite'])` + load `pygments.css`.
- **Frontend:** Jinja2 + CSS minimalis. Form wajib `{{ csrf_token() }}`. Validasi server-side ketat.
- **Git:** `.gitignore` (`.db`, `venv/`, `__pycache__/`, `.env`), commit per fitur, `dev`→`main` merge.

**5. Pengujian**
- **Unit:** CRUD kategori, junction table consistency, slug uniqueness, login session, Markdown render kode.
- **Keamanan:** SQLi (`' OR 1=1`), XSS (`<script>`), CSRF bypass, akses `/data/` (403), password plaintext, session fixation.
- **UI/UX:** Mobile, filter kategori sinkron, kode tidak overflow, form admin validasi kosong/invalid.
- **Performa:** Join query <50ms, Gunicorn 2–4 worker, static cache, no memory leak di stress test sederhana.

**6. Deployment (Proxmox Self-Hosted)**
- **Prep Container/VM:** Buat LXC/VM Ubuntu 22.04 di Proxmox. Alokasi: 1–2 vCPU, 1GB RAM, 10GB disk. Enable `Nesting` (jika butuh Docker nanti), set `Proxmox Firewall` default deny.
- **OS Setup:** `apt update && apt upgrade -y` → `apt install python3-venv python3-dev nginx certbot python3-certbot-nginx sqlite3 ufw`
- **App Setup:** 
  1. Clone/push code ke server (`/opt/portfolio`).
  2. `python3 -m venv venv` → `pip install -r requirements.txt`.
  3. Init DB: `sqlite3 data/portfolio.db < schema.sql` → `chmod 750 data/` → `chmod 600 data/portfolio.db` → `chown -R www-data:www-data data/`
- **Systemd Service:** `/etc/systemd/system/portfolio.service`
  ```ini
  [Unit]
  Description=Portfolio Gunicorn
  After=network.target

  [Service]
  User=www-data
  Group=www-data
  WorkingDirectory=/opt/portfolio
  ExecStart=/opt/portfolio/venv/bin/gunicorn -b 127.0.0.1:8000 --workers 2 --timeout 30 app:app
  Restart=always

  [Install]
  WantedBy=multi-user.target
  ```
  → `systemctl enable --now portfolio`
- **Nginx & HTTPS:** `/etc/nginx/sites-available/portfolio`
  ```nginx
  server {
      listen 80;
      server_name yourdomain.com;
      location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }
      location /data/ { deny all; }
      location ~ /\. { deny all; }
      location /static/ { alias /opt/portfolio/static/; expires 30d; }
  }
  ```
  → `ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/` → `nginx -t` → `systemctl reload nginx` → `certbot --nginx -d yourdomain.com`
- **Backup Proxmox:** Aktifkan `Proxmox Backup Scheduler` (LXC/VM dump mingguan). Tambah cron lokal: `0 2 * * * cp /opt/portfolio/data/portfolio.db /opt/backup/portfolio_$(date +\%F).db`
- **Firewall:** `ufw allow 22,80,443/tcp` → `ufw enable`.

**7. Pemeliharaan**
- **Update:** Bulanan `pip list --outdated`, patch dependensi kritis. Host OS update terpisah via Proxmox shell.
- **Monitoring:** `journalctl -u portfolio -f`, log Nginx error, resource monitor Proxmox (CPU/RAM/Disk <70%).
- **Backup:** Verifikasi restore DB 1x/bulan. Simpan `.db` & kode di repo privat terenkripsi.
- **Audit:** Kuartalan cek header (CSP, HSTS, X-Frame-Options), validasi permission `.db`, scan `pip-audit`, rotasi password admin.

🔒 **Anti-Error Checklist (Wajib):**
1. `PRAGMA foreign_keys = ON;` di setiap `get_db()` call.
2. Update kategori write-up: `DELETE FROM writeup_categories WHERE writeup_id=?` → `INSERT OR IGNORE` batch baru.
3. Form admin wajib `{{ form.hidden_tag() }}` (Flask-WTF CSRF).
4. Load `pygments.css` di `<head>` agar kode tidak polos.
5. `.db` di `/opt/portfolio/data/`, block `/data/` di Nginx, permission `600` owner `www-data`.
6. Jalankan via `gunicorn`, jangan `flask run` di produksi.

Mau file `app.py`, `schema.sql`, `portfolio.service`, & `nginx.conf` siap copy-paste? Sebutkan.
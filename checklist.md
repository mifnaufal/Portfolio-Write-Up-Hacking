**Checklist SDLC Progresif (Flask + SQLite + Proxmox)**
✅ Selesai | ⏳ Jalan | ❌ Blok

---

**📦 1. Setup Awal & Repo**
- [ ] Buat repo Git + `.gitignore` (`.db`, `venv/`, `__pycache__/`, `.env`)
- [ ] Init struktur folder (`app.py`, `data/`, `templates/`, `static/`, `config.py`)
- [ ] Buat `venv` lokal + `pip install flask markdown pygments bcrypt gunicorn Flask-WTF`
- [ ] Buat `requirements.txt`
- [ ] Commit `v0.1-init`
🔹 *Output:* Repo bersih, env siap. 🔹 *Verifikasi:* `pip list` sesuai, `.gitignore` aktif.

---

**🗃️ 2. Desain & Skema DB**
- [ ] Tulis `schema.sql` (4 tabel + FK + indeks `slug`)
- [ ] Validasi relasi: `writeup_categories` (junction, `ON DELETE CASCADE`)
- [ ] Siapkan route list (`/`, `/category/<slug>`, `/w/<slug>`, `/search`)
- [ ] Siapkan route admin (`/admin/*` CRUD + login)
🔹 *Output:* `schema.sql` final, daftar route. 🔹 *Verifikasi:* `sqlite3 portfolio.db < schema.sql` jalan tanpa error.

---

**⚙️ 3. Backend (Flask)**
- [ ] Setup `app.py`: config, DB helper (`PRAGMA foreign_keys=ON;`)
- [ ] Implementasi auth admin (`bcrypt`, session, `Flask-WTF` CSRF)
- [ ] CRUD Kategori (auto-generate slug, validasi unik)
- [ ] CRUD Write-Up (Markdown parse, sync junction: `DELETE` lama → `INSERT` baru)
- [ ] Route publik + query join 3 tabel untuk filter kategori
🔹 *Output:* `app.py` fungsional lokal. 🔹 *Verifikasi:* Postman/cURL test semua endpoint, session & CSRF aktif.

---

**🎨 4. Frontend & Template**
- [ ] `base.html`: layout, CSS reset, Pygments highlight CSS, meta security
- [ ] `index.html` + filter kategori JS
- [ ] `writeup.html`: render `content_md` aman
- [ ] `admin/`: login, form kategori, form write-up (multi-select kategori)
- [ ] Responsif test (mobile/tablet)
🔹 *Output:* UI siap pakai. 🔹 *Verifikasi:* Tidak ada console error, kode hacking tampil rapi, form validasi jalan.

---

**🛡️ 5. Pengujian**
- [ ] Unit: CRUD konsisten, slug unik, junction table sinkron
- [ ] Keamanan: SQLi (`' OR 1=1`), XSS (`<script>`), CSRF bypass, session fixation
- [ ] Akses file: `/data/`, `/.db`, `/../` → harus 403/404
- [ ] Performa: query <50ms, page load <1s, static cache header
- [ ] Fix bug → commit `v0.5-stable`
🔹 *Output:* Bug fixed, siap deploy. 🔹 *Verifikasi:* Semua test pass, tidak ada warning server.

---

**🖥️ 6. Deployment Proxmox**
- [ ] Buat LXC/VM Ubuntu 22.04 (1-2 vCPU, 1GB RAM, 10GB disk)
- [ ] `apt update && apt install python3-venv nginx ufw certbot python3-certbot-nginx sqlite3`
- [ ] Upload code ke `/opt/portfolio`
- [ ] Setup venv server + `pip install -r requirements.txt`
- [ ] Init DB di server: `chmod 750 data/`, `chmod 600 data/portfolio.db`, `chown -R www-www-data data/`
- [ ] Buat `/etc/systemd/system/portfolio.service` → `enable --now`
- [ ] Nginx: proxy ke `127.0.0.1:8000`, block `/data/`, cache `/static/`
- [ ] UFW: `allow 22,80,443/tcp` → `enable`
- [ ] Certbot: `--nginx -d domain.com` → HTTPS aktif
🔹 *Output:* Web live, HTTPS, auto-start. 🔹 *Verifikasi:* `systemctl status portfolio`, `nginx -t`, curl HTTPS 200.

---

**🔄 7. Backup & Monitoring**
- [ ] Cron lokal: `0 2 * * * cp /opt/portfolio/data/portfolio.db /opt/backup/portfolio_$(date +\%F).db`
- [ ] Rotasi: `find /opt/backup -mtime +7 -delete`
- [ ] Proxmox: schedule backup LXC/VM mingguan
- [ ] Log: `journalctl -u portfolio -f`, Nginx error log
- [ ] Test restore DB 1x
🔹 *Output:* Backup otomatis, log terpantau. 🔹 *Verifikasi:* File backup ada, restore jalan tanpa corrupt.

---

**📌 8. Finalisasi**
- [ ] README: cara run lokal, deploy, backup/restore, reset admin
- [ ] Hapus file dev/test, tag `v1.0`
- [ ] Dokumentasi header keamanan (HSTS, CSP, X-Frame-Options)
🔹 *Output:* Proyek closed. 🔹 *Verifikasi:* Repo clean, dokumentasi lengkap, siap maintenance.

**Tips Progres:** Kerjakan 1 fase → commit → test → checklist ✅. Jangan loncat ke deployment sebelum fase 5 pass semua. Mau template `app.py`/`schema.sql`/`service`/`nginx.conf` siap paste? Sebutkan.

# myxl-cli Web Adapter (tanpa mengubah fungsi)

Adapter ini menambahkan **versi Web** untuk proyek `myxl-cli` tanpa mengubah fungsi/berkas asli.
Semua file web berada di folder `webapp/`. Backend memakai **FastAPI** dan hanya memanggil fungsi-fungsi yang sudah ada.

## Struktur
```
.
├─ (berkas asli myxl-cli TETAP)
├─ webapp/
│  ├─ app.py              # server FastAPI (adapter)
│  ├─ templates/
│  │  ├─ index.html
│  │  ├─ login.html
│  │  └─ dashboard.html
│  └─ static/
│     └─ styles.css
├─ requirements-web.txt
├─ Dockerfile
├─ render.yaml            # (opsional) Deploy 1-klik ke Render
└─ .github/workflows/build-publish.yml  # (opsional) build image ke GHCR
```

## Menjalankan secara lokal (tanpa mengubah fungsi)
1. Pastikan dependency asli terpasang:
   ```bash
   pip install -r requirements.txt
   ```
2. Pasang dependency web:
   ```bash
   pip install -r requirements-web.txt
   ```
3. Set **MYXL_API_KEY** (direkomendasikan via environment):
   ```bash
   export MYXL_API_KEY="ISI_API_KEY_ANDA"
   ```
   > Alternatif dev: tulis `api.key` di root repo berisi satu baris API key.
4. Jalankan server:
   ```bash
   uvicorn webapp.app:app --host 0.0.0.0 --port 8000
   ```
5. Buka `http://localhost:8000`

## Deploy dari GitHub (3 opsi)
### Opsi A — Render (paling mudah)
1. Push repo ini ke GitHub Anda (lihat langkah “Push ke GitHub” di bawah).
2. Di Render.com → **New +** → **Blueprint** → pilih repo Anda → Render otomatis membaca `render.yaml`.
3. Pada **Environment Variables**, tambah `MYXL_API_KEY` (tanpa tanda kutip).
4. Deploy. URL web akan diberikan oleh Render (contoh: `https://myxl-cli-web.onrender.com`).

### Opsi B — Docker image via GitHub Actions (GHCR)
1. Aktifkan **Actions** di repo GitHub Anda.
2. Setel workflow ini akan build image dan push ke `ghcr.io/<org>/myxl-cli-web:latest` saat push ke `main`.
3. Jalankan container di server/VPS Anda:
   ```bash
   docker run -d --name myxl-web -e MYXL_API_KEY="..." -p 8000:8000 ghcr.io/<org>/myxl-cli-web:latest
   ```

### Opsi C — GitHub Codespaces / VPS manual
1. Buka Codespaces atau server SSH Anda.
2. Jalankan langkah “Menjalankan secara lokal”.

## Cara Pakai (Web)
1. **Set API Key** (jika halaman meminta). Disarankan set `MYXL_API_KEY` di environment server.
2. **Login:**
   - Buka menu **Login** → **Request OTP** (masukkan nomor XL format `628...`).
   - Setelah menerima SMS OTP, isi **Submit OTP** (nomor + OTP). Jika sukses, akun tersimpan & aktif.
3. **Dashboard:**
   - Lihat saldo/masa aktif di panel **Saldo**.
   - Muat daftar paket (contoh kategori XUT).
   - **Beli via QRIS** → aplikasi akan generate QR PNG. Scan dengan aplikasi pembayaran yang mendukung QRIS.
   - **Beli via eWallet (DANA/OVO/LinkAja)** → masukkan nomor eWallet. Lanjutkan pembayaran di aplikasi eWallet Anda.

> Catatan: Token/refresh token disimpan oleh modul asli (mis. `refresh-tokens.json`) — adapter ini hanya memanggil fungsi-fungsi yang sudah ada.

## Push ke GitHub
```bash
git init
git remote add origin https://github.com/<user>/<repo>.git
git add .
git commit -m "feat(web): add FastAPI adapter without changing original functions"
git branch -M main
git push -u origin main
```

## Keamanan
- Simpan `MYXL_API_KEY` sebagai **environment variable** di platform (Render/VPS). Jangan commit ke Git.
- Endpoint ini adalah adapter internal — tambahkan reverse proxy / auth tambahan jika perlu.
```

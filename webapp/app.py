
# webapp/app.py
# FastAPI adapter for myxl-cli (NO changes to original functions).
# It imports the existing myxl-cli modules and exposes HTTP endpoints.
# Run with: uvicorn webapp.app:app --host 0.0.0.0 --port 8000
import os, sys, io, base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Make sure we can import the original CLI modules no matter where this runs.
# Expectation: this file lives at <repo_root>/webapp/app.py and original code at <repo_root>/
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import original modules (UNCHANGED)
from auth_helper import AuthInstance
from api_request import get_otp, submit_otp, get_balance, get_package
from paket_xut import get_package_xut
from purchase_api import (
    get_payment_methods,
    settlement_qris,
    get_qris_code,
    settlement_multipayment,
)

# Optional: qrcode just to render QR images on the web (does not modify original logic)
import qrcode

app = FastAPI(title="myxl-cli Web Adapter", version="1.0.0")

# Static and templates
STATIC_DIR = REPO_ROOT / "webapp" / "static"
TEMPLATE_DIR = REPO_ROOT / "webapp" / "templates"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

def ensure_api_key_loaded() -> None:
    if not AuthInstance.api_key:
        # Try environment variable first (recommended on cloud hosts)
        env_key = os.getenv("MYXL_API_KEY", "").strip()
        if env_key:
            AuthInstance.api_key = env_key
        else:
            # If not set, try to read from repo_root/api.key (for local/dev usage)
            key_file = REPO_ROOT / "api.key"
            if key_file.exists():
                AuthInstance.api_key = key_file.read_text(encoding="utf-8").strip()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    ensure_api_key_loaded()
    active = AuthInstance.get_active_user()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_user": active,
        "api_key_set": bool(AuthInstance.api_key),
    })

@app.post("/api/api-key")
def set_api_key(api_key: str = Form(...)):
    # Do not store permanently here; user can mount via env var or save to api.key file
    AuthInstance.api_key = api_key.strip()
    if not AuthInstance.api_key:
        raise HTTPException(status_code=400, detail="API key kosong.")
    return {"ok": True}

@app.post("/api/login/request-otp")
def request_otp(contact: str = Form(...)):
    ensure_api_key_loaded()
    if not AuthInstance.api_key:
        raise HTTPException(status_code=400, detail="Set MYXL_API_KEY terlebih dahulu.")
    # Delegates to original function
    res = get_otp(contact.strip())
    # get_otp prints results to stdout; we just answer success here.
    return {"ok": True, "message": "OTP dikirim (cek SMS MyXL Anda)."}

@app.post("/api/login/submit-otp")
def do_submit_otp(contact: str = Form(...), otp: str = Form(...)):
    ensure_api_key_loaded()
    if not AuthInstance.api_key:
        raise HTTPException(status_code=400, detail="Set MYXL_API_KEY terlebih dahulu.")
    # Will save tokens via original save_tokens()
    submit_otp(contact.strip(), otp.strip())
    # Make this number active
    try:
        AuthInstance.set_active_user(int(contact.strip()))
    except Exception:
        pass
    active = AuthInstance.get_active_user()
    return {"ok": True, "active_user": active}

@app.get("/api/me")
def me():
    ensure_api_key_loaded()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        return {"ok": False, "message": "Belum login / belum ada user aktif."}
    bal = get_balance(AuthInstance.api_key, tokens["id_token"])
    return {"ok": True, "balance": bal, "active_user": AuthInstance.get_active_user()}

@app.get("/api/packages/xut")
def packages_xut():
    ensure_api_key_loaded()
    packages = get_package_xut()
    if packages is None:
        raise HTTPException(status_code=400, detail="Tidak ada token aktif atau gagal memuat paket.")
    return {"ok": True, "packages": packages}

@app.get("/api/package")
def package_detail(code: str):
    ensure_api_key_loaded()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        raise HTTPException(status_code=400, detail="Belum login.")
    pkg = get_package(AuthInstance.api_key, tokens, code)
    return {"ok": True, "package": pkg}

@app.post("/api/purchase/qris")
def purchase_qris(code: str = Form(...), price: int = Form(...)):
    """
    Create a QRIS payment and return a QR image as PNG (base64) + raw string.
    This uses original helper functions (no modifications).
    """
    ensure_api_key_loaded()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        raise HTTPException(status_code=400, detail="Belum login.")
    # 1) payment methods (token + timestamp)
    pm = get_payment_methods(
        api_key=AuthInstance.api_key,
        tokens=tokens,
        token_confirmation="",  # according to original flow, confirmation token may be optional here
        payment_target=code,
    )
    token_payment = pm["token_payment"]
    ts_to_sign = pm["timestamp"]
    # 2) settlement to create transaction id
    tx_id = settlement_qris(
        api_key=AuthInstance.api_key,
        tokens=tokens,
        token_payment=token_payment,
        ts_to_sign=ts_to_sign,
        payment_target=code,
        price=int(price),
        item_name="",
    )
    if not tx_id:
        raise HTTPException(status_code=500, detail="Gagal membuat transaksi QRIS.")
    # 3) fetch QR data string
    qris_str = get_qris_code(AuthInstance.api_key, tokens, tx_id)
    if not qris_str:
        raise HTTPException(status_code=500, detail="Gagal mengambil QRIS code.")
    # Render PNG (keep original logic intact; rendering here is only for the web UI)
    img = qrcode.make(qris_str)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64png = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "transaction_id": tx_id, "qris": qris_str, "qris_png_base64": b64png}

@app.post("/api/purchase/ewallet")
def purchase_ewallet(code: str = Form(...), price: int = Form(...), wallet_number: str = Form(...), method: str = Form("DANA")):
    """
    Create an eWallet payment (DANA/OVO/LinkAja, etc.) via the original settlement_multipayment.
    Returns transaction id only; user completes payment in their wallet app.
    """
    ensure_api_key_loaded()
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        raise HTTPException(status_code=400, detail="Belum login.")
    pm = get_payment_methods(
        api_key=AuthInstance.api_key,
        tokens=tokens,
        token_confirmation="",
        payment_target=code,
    )
    token_payment = pm["token_payment"]
    ts_to_sign = pm["timestamp"]
    tx_id = settlement_multipayment(
        api_key=AuthInstance.api_key,
        tokens=tokens,
        token_payment=token_payment,
        ts_to_sign=ts_to_sign,
        payment_target=code,
        price=int(price),
        wallet_number=wallet_number,
        item_name="",
        payment_method=method
    )
    if not tx_id:
        raise HTTPException(status_code=500, detail="Gagal membuat transaksi eWallet.")
    return {"ok": True, "transaction_id": tx_id}

# ----- Simple HTML pages (Jinja) -----

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    ensure_api_key_loaded()
    return templates.TemplateResponse("login.html", {"request": request, "api_key_set": bool(AuthInstance.api_key)})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    ensure_api_key_loaded()
    active = AuthInstance.get_active_user()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_user": active,
        "api_key_set": bool(AuthInstance.api_key),
    })

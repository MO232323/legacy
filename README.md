# Legacies Realty — Land Sales Platform (Malawi)

Professional full-stack system for a land / plot sales company with **unique sale agreements + QR verification**, **photo listings**, and **WhatsApp contact** on every plot.

---

## Features

### Public website
- Modern navy + red branding
- Beautiful plot listings with photos
- Plot detail pages with gallery
- **WhatsApp button** on every listing (pre-filled message)
- Ownership verification (`/verify?ref=LR-2026-BLY-0001`)
- Printable sale agreement with QR
- Book free viewing form

### Admin panel (`/admin`)
- Dashboard, plots CRUD
- **Upload 2–3 photos** when adding/editing a plot
- Create sale agreements → auto reference + QR
- Viewing request leads

### Technical
- Python Flask + SQLAlchemy
- SQLite by default
- QR codes via `segno` (pure Python — works on Windows / Python 3.14)
- Image uploads to `static/uploads/plots/`

---

## Quick start

```bash
cd four-beacons-flask
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
python run.py
```

- **Website:** http://127.0.0.1:5000  
- **Admin:** http://127.0.0.1:5000/admin  
- **Login:** `admin` / `Legacies2026!`

### Demo verification references
| Reference | Buyer |
|-----------|--------|
| `LR-2026-BLY-0001` | Grace Banda |
| `LR-2026-LLW-0002` | James Phiri |
| `LR-2026-MZZ-0003` | Tendai Mwale |

---

## Configuration

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Session secret |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin login |
| `PUBLIC_BASE_URL` | Domain used in QR codes |
| `WHATSAPP_NUMBER` | Digits only with country code, e.g. `265991234567` |

Set `WHATSAPP_NUMBER` to your real business WhatsApp so listing buttons open the correct chat.

---

## Client handover

1. Change admin password and `SECRET_KEY`
2. Set `WHATSAPP_NUMBER` and `PUBLIC_BASE_URL`
3. Update contact email in templates if needed
4. Add real plot photos via Admin → Plots

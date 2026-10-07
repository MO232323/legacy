# Legacies Realty — Land Sales Platform (Malawi)

Professional full-stack system for a land / plot sales company with **Sites → Plots hierarchy**, **Land Purchase Certificates + QR verification**, **photo listings**, and **WhatsApp contact**.

---

## Data model

- **Site** — a development/estate (name, city, description, photos, site plan, location)
- **Plot** — individual unit within a site (code, size, price, status). Certificate is issued **per plot**.
- **Land Purchase Certificate** — replaces “sale agreement”; unique reference + QR

Public flow:
1. Listing shows **sites**
2. Click a site → description, images, layout plan, location + **all plots** on that site
3. Click a plot → plot-only details (size, price, status) + WhatsApp

Admin flow:
1. **Add site** → enter site name + number of plots → fill each plot’s details
2. Description / images / site plan are attached to the **site**
3. Issue a **Land Purchase Certificate** for any available plot

---

## Quick start

```bash
cd legacy-main
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
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
| `DATABASE_URL` | Optional Postgres URL (default SQLite) |
| `CLOUDINARY_URL` | Optional — photos survive redeploys on Render |

---

## Client handover

1. Change admin password and `SECRET_KEY`
2. Set `WHATSAPP_NUMBER` and `PUBLIC_BASE_URL`
3. Update contact email in templates if needed
4. Add real sites via Admin → Sites & Plots

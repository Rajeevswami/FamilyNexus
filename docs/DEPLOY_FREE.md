# FamilyNexus — Free Deployment Guide

Poora stack **₹0/month** mein live karo. Har step copy-paste ready hai.

Ye guide 8 October 2026 ke free tiers ke hisaab se likhi gayi hai.

---

## Sabse pehle: 30-second summary

Deploy ka **order** aisa hai — isse ulta karne pe errors aayenge:

```
1. Neon    → Postgres URL lo
2. Upstash → Redis URL lo
3. R2      → 4 keys lo
4. Render  → Blueprint apply karo, upar ki keys daalo
5. Render  → Static site ka VITE_API_BASE_URL set karo
6. App     → signup karo, family banao
7. UptimeRobot → service ko jagta rakho
```

**Kyun ye order?** Backend ko deploy karte waqt database, Redis aur storage ki keys **pehle se ready** honi chahiye — warna pehla deploy fail hoga aur aapko dobara karna padega.

**Total time:** ~20 minute. **Kharcha:** ₹0.

---

## 1. Free tools — kaun kya karega

| Kaam | Free Tool | Free mein kya milta hai | Card chahiye? |
| --- | --- | --- | --- |
| **Backend** (Django API) | **Render** Free Web Service | 750 ghante/month, 512 MB RAM, auto HTTPS | Nahi |
| **Database** (Postgres) | **Neon** | 1 GB storage, 100 CU-hours/month, kabhi expire nahi | Nahi |
| **Cache + Rate limit** (Redis) | **Upstash** | 500K commands/month, 256 MB, permanent | Nahi |
| **Frontend** (React) | **Render** Static Site | Unlimited bandwidth, kabhi sleep nahi | Nahi |
| **Files** (documents, photos) | **Cloudflare R2** | 10 GB storage, zero egress fee | Nahi |
| **Code + CI** | **GitHub** | Private repo, Actions CI free | Nahi |
| **Uptime monitor** | **UptimeRobot** | 50 monitors, 5-min interval | Nahi |
| **Errors** | **Sentry** | 5,000 errors/month, 1 user | Nahi |

### Kyun ye combination?

- **Render ka free Postgres 30 din baad expire ho jaata hai** — data delete ho jaata hai. Isliye database **Neon** pe rakha hai, jo permanent free hai. Ye FamilyNexus ke "data permanent save" requirement ka core hai.
- **Redis optional nahi hai** — iske bina login 500 deta hai (cache + throttling ispe depend karta hai). Upstash ka free tier permanent hai.
- **Render ka free instance disk ephemeral hai.** Deploy ya restart pe sab uploads gayab. Isliye media **Cloudflare R2** pe jaata hai. Settings khud switch kar leti hain jab `AWS_*` keys milti hain.

### Free tier ke limits — ye pehle se jaan lo

| Cheez | Limit | Asar |
| --- | --- | --- |
| Render free API | 15 min idle ke baad sleep, ~1 min cold start | Pehla request slow lagega. UptimeRobot ping laga do. |
| Render free | 5 GB bandwidth/month | Chhote app ke liye kaafi. |
| Render free | Outbound SMTP band | Real email ke liye SendGrid (API) use karo, SMTP nahi. |
| Neon free | 1 GB Postgres | Indexes bhi count hote hain. Bahut chhota nahi, par monitor karo. |
| Neon free | 5 min idle ke baad scale-to-zero | Cold query ~1 second. |
| Upstash free | 500K commands/month | ~11 commands/minute sustained. |
| R2 free | 10 GB storage | Documents ke liye bahut zyada. |

---

## 2. Pehle local pe chalao (5 minute)

Ye step isliye ki kuch bhi galat ho to pehle yahin pata chale.

```bash
# --- Backend ---
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env

# SECRET_KEY banao
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
# .env mein SECRET_KEY=<jo print hua> daal do

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

```bash
# --- Frontend (naya terminal) ---
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

Kholo: <http://localhost:5173/welcome>

**Zaroori:** local pe Postgres aur Redis chahiye. Docker se:

```bash
docker compose up -d db redis
```

Test chalao:

```bash
cd backend && pytest                    # 294 tests
cd frontend && npm run test && npm run build
```

---

## 3. Database banao (Neon) — 3 minute

1. <https://neon.tech> pe GitHub se sign in karo.
2. **Create project** → Region: **Singapore** (India ke liye sabse paas).
3. Connection string copy karo — aisi dikhegi:
   ```
   postgresql://neondb_owner:npg_XXXX@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **`?sslmode=require` hatao mat.** Neon iske bina connect nahi karega.

> Neon ka connection string **pooled** endpoint ke liye bhi milta hai (host mein `-pooler` hota hai). Serverless backend ke liye wahi behtar hai.

---

## 4. Redis banao (Upstash) — 2 minute

1. <https://upstash.com> pe sign in karo.
2. **Create Database** → Type: **Regional** → Region: **ap-south-1 (Mumbai)**.
3. **TLS** enable rehne do.
4. Connection details se **`rediss://`** wala URL copy karo (dhyan do — **do baar `s`**, TLS ke liye):
   ```
   rediss://default:AXxxxxxxxxxxxxxxxxxxxx@ap-south-1-xxxxx.upstash.io:6379
   ```

---

## 5. File storage banao (Cloudflare R2) — 5 minute

Ye step skip kar sakte ho, **lekin** tab har deploy pe uploads delete honge.

1. Cloudflare account → **R2** → **Create bucket** → naam: `familynexus-media`
2. **Settings** → **Public access** → **R2.dev subdomain** allow karo.
3. **Manage API Tokens** → **Create API token** → Permission: **Object Read & Write**
4. Ye 4 values note karo:

   | Value | Kahan milegi |
   | --- | --- |
   | **Account ID** | R2 overview page |
   | **Access Key ID** | Token banate waqt |
   | **Secret Access Key** | Token banate waqt (sirf ek baar dikhti hai) |
   | **Endpoint** | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |

---

## 6. Backend deploy karo (Render) — 5 minute

### 6a. Code GitHub pe bhejo

```bash
cd FamilyNexus
git add .
git commit -m "deploy to render"
git push origin main
```

> Agar aap Arena branch pe ho (`arena/...`), to pehle PR merge karo ya `main` pe push karo — Render `main` branch se deploy karta hai.

### 6b. Render pe Blueprint banao

1. <https://render.com> kholo → **Get Started** → **GitHub** se sign in karo
2. GitHub ko authorize karo (repo access do)
3. Dashboard pe **New +** → **Blueprint**
4. `Rajeevswami/FamilyNexus` repo select karo → **Connect**
5. Render `render.yaml` padh lega aur **do services** dikhayega:
   - `familynexus-api` (Python web service)
   - `familynexus-web` (Static site)
6. Blueprint ka naam: `familynexus` → **Apply**

### 6c. Render jo values maangega, ye daalo

Ye table copy karke rakh lo — Render ek-ek karke poochhega:

| Key | Value | Kahan se |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://...neon.tech/neondb?sslmode=require` | Step 3 |
| `REDIS_URL` | `rediss://default:...@...upstash.io:6379` | Step 4 |
| `FIELD_ENCRYPTION_KEY` | Neeche command chalao | — |
| `AWS_STORAGE_BUCKET_NAME` | `familynexus-media` | Step 5 |
| `AWS_ACCESS_KEY_ID` | R2 Access Key ID | Step 5 |
| `AWS_SECRET_ACCESS_KEY` | R2 Secret Access Key | Step 5 |
| `AWS_S3_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` | Step 5 |
| `AWS_S3_REGION_NAME` | `auto` | — |
| `CORS_ALLOWED_ORIGINS` | `https://familynexus-web.onrender.com` | Render aapko URL dega |
| `CSRF_TRUSTED_ORIGINS` | `https://familynexus-web.onrender.com` | same |
| `FRONTEND_URL` | `https://familynexus-web.onrender.com` | same |

**`FIELD_ENCRYPTION_KEY` banane ke liye:**
```bash
cd backend
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Ye poori line copy karo: gAAAAAB...
```

> **Tip:** Render service URL pehle deploy ke baad milta hai (`familynexus-web.onrender.com`). Naam pehle se pata hai kyunki `render.yaml` mein wahi rakha hai. Agar Render naam badal de, to env vars baad mein update kar dena.

### 6d. Pehla deploy (~5 minute)

Render automatically:
1. `pip install -r requirements/prod.txt` chalata hai
2. `bash ../scripts/release.sh` chalata hai — jo migrations apply karta hai, static files collect karta hai, phir gunicorn start karta hai
3. `/api/v1/health/` poll karta hai — 200 mile to "Live" ho jaata hai

Deploy logs mein ye dikhna chahiye:
```
==> Checking configuration
==> Applying database migrations
  Applying accounts.0001_initial... OK
  ...
==> Collecting static files
163 static files copied
==> Starting gunicorn on port 10000 with 3 worker(s)
```

**Verify karo:**
```bash
curl https://familynexus-api.onrender.com/api/v1/health/
# {"success":true,"data":{"status":"ok","database":"ok","cache":"ok"}}
```

| Key | Value |
| --- | --- |
| `DATABASE_URL` | Neon ka connection string (step 3) |
| `REDIS_URL` | Upstash ka `rediss://` URL (step 4) |
| `FIELD_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `AWS_STORAGE_BUCKET_NAME` | `familynexus-media` |
| `AWS_ACCESS_KEY_ID` | R2 Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | R2 Secret Access Key |
| `AWS_S3_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `AWS_S3_REGION_NAME` | `auto` |
| `CORS_ALLOWED_ORIGINS` | `https://familynexus-web.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://familynexus-web.onrender.com` |
| `FRONTEND_URL` | `https://familynexus-web.onrender.com` |

5. **Apply** dabao. Pehla deploy ~5 minute lega.

Deploy `scripts/release.sh` chalata hai, jo:
- `check --deploy` chalata hai,
- migrations apply karta hai,
- `collectstatic` karta hai,
- gunicorn start karta hai `$PORT` pe.

**Verify karo:**
```bash
curl https://familynexus-api.onrender.com/api/v1/health/
# {"success":true,"data":{"status":"ok","database":"ok","cache":"ok"}}
```

Teeno `"ok"` hone chahiye. `"cache":"error"` = REDIS_URL galat hai.
`database":"error"` = `DATABASE_URL` galat hai, ya `?sslmode=require` missing hai.

### `ALLOWED_HOSTS` ki galti se bacho

Deploy ke baad agar log mein ye dikhe:
```
Invalid HTTP_HOST header: 'familynexus-api.onrender.com'.
You may need to add 'familynexus-api.onrender.com' to ALLOWED_HOSTS.
```

To `ALLOWED_HOSTS` mein apna Render hostname daalo. Ya `render.yaml` jaisa `.onrender.com` likh do — **aage ka dot** mat bhoolna, isse har subdomain chalta hai:

```
ALLOWED_HOSTS=.onrender.com
```

Custom domain lagane ke baad `api.tumharadomain.com` bhi add karo, warna API 400 dega.

---

## 7. Frontend deploy karo (Render Static Site) — 3 minute

`render.yaml` already `familynexus-web` bana deta hai. Sirf ek value daalo:

| Key | Value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://familynexus-api.onrender.com/api/v1` |

Steps:
1. Render dashboard → `familynexus-web` → **Environment**
2. **Add Environment Variable** → `VITE_API_BASE_URL` = `https://familynexus-api.onrender.com/api/v1`
3. **Manual Deploy** → **Clear build cache & deploy** ← ye zaroori hai

> **Dhyan do:** `VITE_*` values **build time** pe JavaScript mein bake ho jaati hain. Sirf env var badalne se kuch nahi hoga — **clear build cache** wala deploy karna padega, warna purani URL hi rahegi.

**Final check:**
```bash
curl -I https://familynexus-web.onrender.com
# HTTP/2 200
# content-security-policy: default-src 'self'; ...
# x-frame-options: DENY
```

---

## 8. Pehla account banao — 2 minute

1. `https://familynexus-web.onrender.com/signup` kholo
2. Naam, email, password daalo
3. Login karo → **Create Family**
4. Family ban jaayegi, aur saath hi chart of accounts + expense categories auto-seed ho jaayenge

**Admin account (optional):**
```bash
# Render dashboard → familynexus-api → Shell
python manage.py createsuperuser
```
Phir `https://familynexus-api.onrender.com/admin/` pe login karo.

---

## 9. Custom domain (free)

1. **Frontend:** Render → `familynexus-web` → Settings → Custom Domain → `app.tumharadomain.com`
   DNS: `CNAME app → familynexus-web.onrender.com`
2. **Backend:** Render → `familynexus-api` → Custom Domain → `api.tumharadomain.com`
   DNS: `CNAME api → familynexus-api.onrender.com`
3. Render SSL khud laga dega (Let's Encrypt, free).
4. **Ab ye 3 env vars update karo** aur redeploy:
   - Backend: `ALLOWED_HOSTS=api.tumharadomain.com`, `CORS_ALLOWED_ORIGINS=https://app.tumharadomain.com`, `CSRF_TRUSTED_ORIGINS=https://app.tumharadomain.com`, `FRONTEND_URL=https://app.tumharadomain.com`
   - Frontend: `VITE_API_BASE_URL=https://api.tumharadomain.com/api/v1` + **clear build cache deploy**

---

## 10. Sleep se bachao (free)

Render free service 15 min idle ke baad soti hai. Free fix:

1. <https://uptimerobot.com> pe sign up karo
2. **Add Monitor** → Type: **HTTP(s)**
3. URL: `https://familynexus-api.onrender.com/api/v1/health/`
4. Interval: **5 minutes**

Bas — service jagti rahegi.

---

## 11. Production checklist

Deploy se pehle ye sab hona chahiye:

```bash
cd backend
python manage.py check --deploy          # 0 security warnings
python manage.py tenant_isolation_audit  # No unscoped tenant models.
python manage.py check_secrets           # Required secrets are set.
```

| Cheez | Kahan check karo |
| --- | --- |
| `DEBUG=False` | Render env vars |
| `SECRET_KEY` 50+ random chars | Render `generateValue` karta hai |
| HTTPS redirect on | `SECURE_SSL_REDIRECT=True` (production settings) |
| HSTS 1 year | `SECURE_HSTS_SECONDS=31536000` |
| Secure cookies | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| CSP header | `curl -I https://api.../api/v1/health/` |
| Rate limit | 11 baar galat login → HTTP **429** |
| Tenant isolation | User B, User A ki family ID maange → **404** |
| Backups | Neon automatic backups (free tier pe limited) |

**Real email chahiye?** Render free outbound SMTP block karta hai. SendGrid ka API use karo:
```
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxx
DEFAULT_FROM_EMAIL=FamilyNexus <no-reply@tumharadomain.com>
```

---

## 12. Deploy ke baad — apna app test karo

```bash
API=https://familynexus-api.onrender.com/api/v1

# 1. Health
curl $API/health/

# 2. Naya account
curl -X POST $API/auth/register/ -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"StrongPass!2026","confirm_password":"StrongPass!2026"}'

# 3. Login
curl -X POST $API/auth/login/ -H "Content-Type: application/json" \
  -d '{"identifier":"test@example.com","password":"StrongPass!2026"}'

# 4. Rate limit kaam kar raha hai?
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code} " -X POST $API/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"identifier":"test@example.com","password":"galat"}'
done
echo ""   # 401 x10 ke baad 429 aana chahiye
```

---

## 13. Common errors — turant fix

| Error / Symptom | Matlab | Fix |
| --- | --- | --- |
| `Invalid HTTP_HOST header` | `ALLOWED_HOSTS` mein hostname nahi hai | `.onrender.com` daalo (leading dot ke saath) |
| `database":"error"` in health | `DATABASE_URL` galat ya SSL missing | `?sslmode=require` add karo |
| `cache":"error"` in health | `REDIS_URL` galat / `redis://` vs `rediss://` | Upstash wala `rediss://` use karo (do `s`) |
| Login pe 500 error | Redis down hai | `REDIS_URL` check karo. Redis ke bina login kaam nahi karta |
| Deploy "unhealthy" | Health check 301 redirect kha raha hai | Code mein already fix hai (`SECURE_REDIRECT_EXEMPT`) |
| Frontend purani API ko call kar raha | `VITE_API_BASE_URL` build-time pe bake hota hai | **Clear build cache & deploy** |
| CORS error browser mein | `CORS_ALLOWED_ORIGINS` mein frontend URL nahi | Exact origin daalo, no trailing slash |
| 403 on POST (CSRF) | `CSRF_TRUSTED_ORIGINS` missing | Frontend URL daalo `https://` ke saath |
| Uploads deploy ke baad gayab | `AWS_*` keys set nahi | Step 5 karo (R2) |
| Rate limit 403 dikh raha | Purana code | Latest code pull karo — ab 429 aata hai |
| `provider_not_configured` | Stripe/Razorpay keys nahi hain | Normal hai. Manual billing chalta hai |

### Neon se connect nahi ho raha?

Neon ka URL `?sslmode=require` ke saath aata hai. Copy karte waqt ye suffix **kaata mat**. Agar password mein `@` ya `#` jaise special characters hain, to unhe URL-encode karna padega.

### Deploy ke baad pehla request slow (30-60 sec)

Render free instance so gaya tha. Ye normal hai — UptimeRobot (step 10) laga do.

---

## 14. Kab paid pe jaana hai

Free tier demo, testing aur personal family ke liye theek hai. Real users aa jaayein to:

| Kab | Kya | Kitna |
| --- | --- | --- |
| Cold start se users pareshaan | Render Starter | $7/month |
| 1 GB DB full | Neon Launch | ~$19/month |
| 500K Redis commands khatam | Upstash Pay-as-you-go | $0.20/100K commands |
| Free API slow | Render Starter | $7/month |

**Sasta upgrade path:** ek **Hetzner CX22** VPS (~€4/month) le lo aur `docker-compose.prod.yml` chala do. Usme Postgres, Redis, Celery, nginx — sab included, koi cold start nahi. Yahi sabse zyada value for money hai.

---

## 15. Aage kya baaki hai

Ye cheezein deployment ke liye zaroori nahi, par launch se pehle dekh lo:

- **Legal pages** — `/legal/terms` aur `/legal/privacy` draft hain. Real users se pehle lawyer se check karwao.
- **pgvector** — free Postgres pe available nahi (Neon pe extension enable kar sakte ho). Abhi JSON embeddings use hote hain.
- **Celery worker** — Render free pe alag service chalane ke liye paisa lagta hai. Iske bina weekly summary email nahi jaayegi (baaki app chalega).
- **Stripe/Razorpay** — real payments ke liye live keys chahiye. Baaki app unke bina chalta hai.

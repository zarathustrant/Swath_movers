# Cloudflare Security Setup for seistools.space

## Current Status

✅ **SSL/TLS is ACTIVE**
- Your site is accessible via HTTPS
- Cloudflare provides free SSL certificate
- Certificate auto-renews

---

## Required Security Configuration

### 1. SSL/TLS Settings

**Go to:** https://dash.cloudflare.com/ → seistools.space → SSL/TLS

#### A. Encryption Mode
**Current Required:** Flexible (since your origin is HTTP)

**Options:**
- ✅ **Flexible** - Cloudflare ↔ Visitor: HTTPS, Cloudflare ↔ Origin: HTTP
- ⚠️ **Full** - Requires SSL on your origin (nginx)
- ⚠️ **Full (Strict)** - Requires valid SSL certificate on origin

**Recommendation:** Keep as **Flexible** for now (it's working).

#### B. Always Use HTTPS
**Path:** SSL/TLS → Edge Certificates → Always Use HTTPS

**Action:** Turn this **ON**

**What it does:** Automatically redirects all HTTP requests to HTTPS

#### C. Minimum TLS Version
**Path:** SSL/TLS → Edge Certificates → Minimum TLS Version

**Recommended:** TLS 1.2 (blocks old/insecure protocols)

---

### 2. Brute Force Protection

Cloudflare provides multiple layers of protection against brute force attacks:

#### A. Security Level
**Path:** Security → Settings → Security Level

**Options:**
- Low - Challenges only most threatening visitors
- Medium - Challenges both moderate and highly threatening visitors ✅ **RECOMMENDED**
- High - Challenges all visitors that have exhibited threatening behavior
- Under Attack - Should only be used if your website is under DDoS attack

**Action:** Set to **Medium**

#### B. Bot Fight Mode (FREE)
**Path:** Security → Bots → Bot Fight Mode

**Action:** Turn **ON**

**What it does:**
- Automatically blocks known bad bots
- Challenges likely bots with CAPTCHA
- Allows good bots (Google, Bing, etc.)

#### C. Rate Limiting (Advanced - Paid Feature)
For free plan, you get basic DDoS protection automatically.

For login endpoints, implement application-level rate limiting (see Flask-Limiter below).

---

### 3. Firewall Rules (Free Plan)

**Path:** Security → WAF

You get 5 free firewall rules. Here are recommended rules:

#### Rule 1: Block Specific Countries (Optional)
If you only serve specific regions:
```
(ip.geoip.country ne "NG") and (ip.geoip.country ne "US") and (ip.geoip.country ne "GB")
```
Action: Block

#### Rule 2: Protect Login Endpoint
```
(http.request.uri.path eq "/login" and http.request.method eq "POST" and not ip.geoip.country in {"NG" "US" "GB"})
```
Action: Challenge (CAPTCHA)

#### Rule 3: Block Known Attack Patterns
```
(http.request.uri.query contains "admin" or http.request.uri.query contains "phpMyAdmin")
```
Action: Block

---

### 4. Additional Security Headers

**Path:** Rules → Transform Rules → Managed Transforms → Security Headers

**Recommended to enable:**
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: SAMEORIGIN
- ✅ X-XSS-Protection

Most of these are already in your nginx config, but Cloudflare adds an extra layer.

---

### 5. Application-Level Brute Force Protection (Flask)

Since Cloudflare free plan doesn't include advanced rate limiting, add protection in your Flask app:

**Install Flask-Limiter:**
```bash
pip install Flask-Limiter
```

**Add to your Flask app:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Protect login endpoint
@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # Your login logic
    pass

# Protect API endpoints
@app.route('/api/upload', methods=['POST'])
@limiter.limit("10 per minute")
def upload():
    # Your upload logic
    pass
```

---

### 6. DDoS Protection

✅ **Already Active** - Cloudflare automatically provides:
- Layer 3/4 DDoS mitigation (network layer)
- Layer 7 DDoS mitigation (application layer)
- Automatic attack detection
- Traffic filtering

**Under Attack Mode:**
If you're actively being attacked:
1. Go to: Security → Settings → Security Level
2. Select: **I'm Under Attack**
3. This shows interstitial challenge to all visitors (5 seconds)

---

### 7. Page Rules for Additional Protection

**Path:** Rules → Page Rules

**Create these rules (you get 3 free):**

#### Rule 1: Cache Everything on Static Files
- URL: `seistools.space/static/*`
- Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month

#### Rule 2: Bypass Cache on Admin/Login
- URL: `seistools.space/login*`
- Settings:
  - Cache Level: Bypass
  - Security Level: High

#### Rule 3: Browser Integrity Check
- URL: `seistools.space/*`
- Settings:
  - Browser Integrity Check: On

---

## Quick Setup Checklist

Run through these in Cloudflare dashboard:

### Essential (Do Now):
- [ ] SSL/TLS → Overview → Set to **Flexible**
- [ ] SSL/TLS → Edge Certificates → **Always Use HTTPS: ON**
- [ ] Security → Settings → Security Level: **Medium**
- [ ] Security → Bots → **Bot Fight Mode: ON**
- [ ] Caching → Configuration → Caching Level: **Standard**
- [ ] Caching → Configuration → Browser Cache TTL: **Respect Existing Headers**

### Recommended (Do Soon):
- [ ] SSL/TLS → Edge Certificates → Minimum TLS Version: **1.2**
- [ ] Security → WAF → Create firewall rule for login protection
- [ ] Add Flask-Limiter to your application
- [ ] Create Page Rules for static files and admin areas

### Optional (Nice to Have):
- [ ] Security → WAF → Block specific countries (if needed)
- [ ] Security → WAF → Block known attack patterns
- [ ] Rules → Transform Rules → Enable security headers

---

## Monitoring & Logs

### Check Security Events:
**Path:** Security → Events

This shows:
- Blocked requests
- Challenged visitors
- Firewall rule matches
- Bot detections

### Check Analytics:
**Path:** Analytics → Traffic

See:
- Request volume
- Bandwidth usage
- Threats mitigated
- Cache performance

---

## Testing Your Security

### Test SSL:
```bash
curl -I https://seistools.space
# Should return HTTP/2 200 with server: cloudflare
```

### Test HTTP Redirect:
```bash
curl -I http://seistools.space
# Should return HTTP/1.1 301 with location: https://
```

### Test Rate Limiting (after adding Flask-Limiter):
```bash
# Send 10 requests quickly to login
for i in {1..10}; do
  curl -X POST https://seistools.space/login
done
# Should get rate limit error after 5 requests
```

---

## What You Already Have (No Action Needed)

✅ **From Cloudflare (Automatic):**
- DDoS protection (all layers)
- SSL/TLS encryption
- Global CDN
- Bot detection
- Threat intelligence

✅ **From Your Nginx Config:**
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Request size limits (50MB)
- Static file serving

---

## Summary

**You're already protected from:**
- ✅ DDoS attacks (automatic)
- ✅ Man-in-the-middle attacks (SSL/TLS)
- ✅ Some basic bot attacks

**You should add:**
- ⚠️ Application-level rate limiting (Flask-Limiter)
- ⚠️ Firewall rules for login endpoint
- ⚠️ Always Use HTTPS (redirect HTTP → HTTPS)

**Cost:** Everything mentioned here is available on Cloudflare's FREE plan!

---

## Need Help?

**Cloudflare Dashboard:** https://dash.cloudflare.com/
**Support Docs:** https://developers.cloudflare.com/
**Security Guide:** https://developers.cloudflare.com/security/

For application-level security questions, check Flask Security documentation.

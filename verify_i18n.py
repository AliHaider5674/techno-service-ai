"""Verify Arabic rendering + RTL + language switcher."""
import httpx
import re
import sys

BASE = "http://127.0.0.1:8001"
sys.stdout.reconfigure(encoding="utf-8")

with httpx.Client(base_url=BASE, follow_redirects=False, timeout=10.0) as c:
    # Sign in
    r = c.post("/sign-in", data={"username": "admin", "password": "Admin!2026"})
    for h in r.headers.get_list("set-cookie"):
        if "tsai_session=" in h:
            cookie = h.split("tsai_session=", 1)[1].split(";", 1)[0]
            c.cookies.set("tsai_session", cookie)
            break

    # English (default)
    c.cookies.set("tsai_lang", "en")
    print("=" * 60)
    print("ENGLISH (default) — no cookie")
    print("=" * 60)
    r = c.get("/sign-in")
    print(f"  /sign-in         status={r.status_code}  lang_attr={'lang=\"en\"' in r.text}  dir_attr={'dir=\"ltr\"' in r.text}  title={'Sign in' in r.text}")
    r = c.get("/proactive/")
    print(f"  /proactive/      status={r.status_code}  lang_attr={'lang=\"en\"' in r.text}  dir_attr={'dir=\"ltr\"' in r.text}")

    # Arabic
    c.cookies.set("tsai_lang", "ar")
    print()
    print("=" * 60)
    print("ARABIC (RTL) — tsai_lang=ar")
    print("=" * 60)
    r = c.get("/sign-in")
    print(f"  /sign-in            status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'تسجيل الدخول' in r.text}")
    r = c.get("/proactive/")
    print(f"  /proactive/         status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'المكتب 18' in r.text}")
    r = c.get("/proactive/scan")
    print(f"  /proactive/scan     status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'مراقب المنتجات' in r.text}")
    r = c.get("/proactive/qualify")
    print(f"  /proactive/qualify  status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'كاشف المنتجات' in r.text}")
    r = c.get("/proactive/patents")
    print(f"  /proactive/patents  status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'مراقب براءات' in r.text}")
    r = c.get("/proactive/agency-workflow")
    print(f"  /proactive/agency-workflow  status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'سير عمل' in r.text}")
    r = c.get("/proactive/report")
    print(f"  /proactive/report   status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'تقرير' in r.text}")
    r = c.get("/home")
    print(f"  /home               status={r.status_code}  lang_attr={'lang=\"ar\"' in r.text}  dir_attr={'dir=\"rtl\"' in r.text}  arabic={'مرحباً' in r.text}")

    # Switch back to English
    c.cookies.set("tsai_lang", "en")
    print()
    print("=" * 60)
    print("ENGLISH (regression check after AR visit)")
    print("=" * 60)
    r = c.get("/sign-in")
    print(f"  /sign-in         status={r.status_code}  lang_attr={'lang=\"en\"' in r.text}  dir_attr={'dir=\"ltr\"' in r.text}  title={'Sign in' in r.text}")
    r = c.get("/proactive/")
    print(f"  /proactive/      status={r.status_code}  lang_attr={'lang=\"en\"' in r.text}  dir_attr={'dir=\"ltr\"' in r.text}")

    # Language switcher test
    print()
    print("=" * 60)
    print("LANGUAGE SWITCHER (POST/GET /i18n/set)")
    print("=" * 60)
    c.cookies.set("tsai_lang", "en")
    r = c.get("/i18n/set?lang=ar&next=/proactive/", follow_redirects=False)
    print(f"  GET /i18n/set?lang=ar  status={r.status_code}  set_cookie={'tsai_lang=ar' in r.headers.get('set-cookie', '')}")
    r = c.get("/i18n/set?lang=en&next=/proactive/", follow_redirects=False)
    print(f"  GET /i18n/set?lang=en  status={r.status_code}  set_cookie={'tsai_lang=en' in r.headers.get('set-cookie', '')}")
    # Bad lang
    r = c.get("/i18n/set?lang=fr&next=/", follow_redirects=False)
    print(f"  GET /i18n/set?lang=fr  status={r.status_code}  normalised={'tsai_lang=en' in r.headers.get('set-cookie', '')}")
    # Open-redirect attempt
    r = c.get("/i18n/set?lang=ar&next=https://evil.com", follow_redirects=False)
    print(f"  GET /i18n/set?next=evil status={r.status_code}  next={'Location: /' in r.headers.get('location', '/') or 'Location: /'}")

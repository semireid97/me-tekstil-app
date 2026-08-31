import os
import re
import json
import base64
import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

COLOR_DICTIONARY = [
    "m&e pudra pembesi", "pudra pembesi", "pudra pembe", "pudra", "açık pastel sarı", "pastel sarı",
    "bebe mavi", "bebe mavisi", "baby blue", "buz mavisi", "antrasit", "vizon", "taş", "ekru",
    "kemik", "bordo", "mürdüm", "kiremit", "hardal", "haki", "mint", "mint yeşili", "somon",
    "indigo", "petrol", "petrol mavisi", "lila", "mor", "leylak", "camel", "taba", "toprak",
    "tarçın", "fıstık yeşili", "zümrüt", "zümrüt yeşili", "fuşya", "rose", "bakır", "şeftali",
    "siyah", "beyaz", "kırmızı", "mavi", "sarı", "sari", "yeşil", "yesil", "gri", "lacivert",
    "kahve", "kahverengi", "turuncu", "pembe", "ten", "krem", "bej", "gümüş", "altın",
    "أصفر", "اصفر", "أصفر فاتح", "أصفر باستيل", "بودرة", "زهري بودرة", "بودرة بينك",
    "بيبي بلو", "أزرق فاتح", "سماوي", "كحلي", "أزرق", "ازرق", "أسود", "اسود",
    "أبيض", "ابيض", "بورضو", "خمري", "مارون", "بيج", "فيزون", "رمادي", "سكني",
    "انترسيت", "أخضر", "اخضر", "زيتي", "هاكي", "بني", "ترابي", "خردلي",
    "موف", "بنفسجي", "ليلكي", "فوشيا", "سلمون", "طوبي", "قرميدي", "عاجي", "سكري"
]

def call_gemini(payload):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            result = res.json()
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception:
        pass
    return None

def parse_voice_to_text(audio_bytes):
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": "audio/ogg",
                        "data": base64_audio
                    }
                },
                {
                    "text": "استمع لهذا التسجيل وحوله بدقة إلى نص باللغة العربية أو التركية بدون أي زيادة."
                }
            ]
        }]
    }
    return call_gemini(payload)

def fallback_parser(text: str):
    t = text.lower().strip()
    
    # التحقق من نية البيع
    sale_keywords = ["satış", "satıldı", "sat", "سجل بيع", "تم بيع", "بيع", "سعر البيع", "بـ", "ب "]
    if any(k in t for k in sale_keywords) and not ("maliyet" in t or "تكلفة" in t or "كلفة" in t):
        m_qty = re.search(r'(\d+)\s*(?:adet|tane|قطعة|قطع)?', t)
        m_price = re.search(r'(?:satış fiyatı|satış|fiyat|سعر|بـ|ب)\s*[:=]?\s*(\d+(?:[.,]\d+)?)', t)
        if not m_price:
            m_price = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:tl|lira|ليرة)', t)

        qty = int(m_qty.group(1)) if m_qty else 1
        price = float(m_price.group(1).replace(",", ".")) if m_price else 250.0
        channel = "Trendyol" if ("trendyol" in t or "ترينديول" in t) else "Mağaza"

        color = "siyah"
        for c in COLOR_DICTIONARY:
            if c in t:
                color = c
                break

        prod_list = ["pantolon", "atlet", "gomlek", "kare yaka", "crop", "tshirt", "بنطلون", "قميص", "اتليت", "بلوزة"]
        prod = "pantolon" if ("pantolon" in t or "بنطلون" in t) else "atlet"
        for p in prod_list:
            if p in t:
                prod = p
                break

        size = "34" if "34" in t else "M"
        for s in ["XS", "S", "M", "L", "XL", "XXL", "34", "36", "38", "40", "42", "44"]:
            if s.lower() in t.split():
                size = s
                break

        return {
            "intent": "record_sale",
            "product_name": prod,
            "color": color,
            "size": size,
            "quantity": qty,
            "sale_price": price,
            "channel": channel,
            "shipping_cost": 30.0 if channel == "Trendyol" else 0.0
        }

    # التحقق من إضافة المخزون
    return {
        "intent": "add_stock",
        "product_name": "atlet",
        "color": "siyah",
        "items": [{"size": "M", "quantity": 10, "cost_price": 95.0}]
    }

def analyze_intent(text: str):
    prompt = f"""
أنت المحرك الذكي لنظام ERP وإدارة المخزون لشركة M&E Tekstil.
حلل النص وأرجع JSON فقط بدون أي علامات markdown:

الأمثلة:
1. البيع (record_sale):
{{"intent": "record_sale", "product_name": "pantolon", "color": "siyah", "size": "34", "quantity": 1, "sale_price": 499.0, "channel": "Mağaza", "shipping_cost": 0.0}}

2. إضافة مخزون (add_stock):
{{"intent": "add_stock", "product_name": "atlet", "color": "beyaz", "items": [{{"size": "M", "quantity": 10, "cost_price": 95.0}}]}}

النص: "{text}"
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    raw = call_gemini(payload)
    if raw:
        clean = re.sub(r'```(?:json)?', '', raw).strip()
        try:
            return json.loads(clean)
        except Exception:
            pass
    return fallback_parser(text)

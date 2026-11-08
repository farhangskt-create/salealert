import json
import os
from datetime import datetime
import requests
from bs4نهار import BeautifulSoup
from bs4 import BeautifulSoup

# پاکستان کے ٹاپ اور ایکٹیو برانڈز کی ماسٹر لسٹ (5 مختلف بیچز میں تقسیم)
ALL_BRANDS = [
    # --- Batch 1: Fashion & Apparel (Part 1) ---
    {"id": "sapphire", "name": "Sapphire", "url": "https://sapphireonline.pk/collections/sale", "category": "Fashion", "batch": 1},
    {"id": "khaadi", "name": "Khaadi", "url": "https://www.khaadi.com/pk/sale", "category": "Fashion", "batch": 1},
    {"id": "outfitters", "name": "Outfitters", "url": "https://outfitters.com.pk/collections/sale", "category": "Fashion", "batch": 1},
    {"id": "junaidjamshed", "name": "J. Junaid Jamshed", "url": "https://www.junaidjamshed.com/sale.html", "category": "Fashion", "batch": 1},

    # --- Batch 2: Fashion & Apparel (Part 2) ---
    {"id": "gulahmed", "name": "Gul Ahmed Ideas", "url": "https://www.gulahmedshop.com/sale", "category": "Fashion", "batch": 2},
    {"id": "sanasafinaz", "name": "Sana Safinaz", "url": "https://sanasafinaz.com/pk/sale.html", "category": "Fashion", "batch": 2},
    {"id": "limelight", "name": "Limelight", "url": "https://www.limelight.pk/collections/sale", "category": "Fashion", "batch": 2},
    {"id": "alkaram", "name": "Alkaram Studio", "url": "https://www.alkaramstudio.com/collections/sale", "category": "Fashion", "batch": 2},

    # --- Batch 3: Electronics & Mobiles ---
    {"id": "daraz", "name": "Daraz PK Flash Sale", "url": "https://www.daraz.pk/flash-sale/", "category": "Electronics & General", "batch": 3},
    {"id": "priceoye", "name": "PriceOye", "url": "https://priceoye.pk/", "category": "Mobiles & Electronics", "batch": 3},
    {"id": "telemart", "name": "Telemart", "url": "https://telemart.pk/collections/sale", "category": "Mobiles & Gadgets", "batch": 3},

    # --- Batch 4: Groceries & Supermarkets ---
    {"id": "carrefour", "name": "Carrefour PK", "url": "https://www.carrefour.pk/mafpak/en/c/FPAK1010000", "category": "Grocery", "batch": 4},
    {"id": "metro", "name": "Metro Online", "url": "https://www.metro-online.pk/", "category": "Grocery", "batch": 4},
    {"id": "alfatah", "name": "Al-Fatah", "url": "https://alfatah.pk/collections/sale", "category": "Grocery & Departmental", "batch": 4},

    # --- Batch 5: Lifestyle & Footwear ---
    {"id": "ndure", "name": "Ndure Shoes", "url": "https://www.ndure.com/collections/sale", "category": "Footwear", "batch": 5},
    {"id": "service", "name": "Servis Shoes", "url": "https://servis.pk/collections/sale", "category": "Footwear", "batch": 5},
    {"id": "stylo", "name": "Stylo", "url": "https://stylo.pk/collections/sale", "category": "Footwear", "batch": 5}
]

TOTAL_BATCHES = 5  # کل 5 بیچز ہیں

def get_today_batch():
    day_of_year = datetime.now().timetuple().tm_yday
    return (day_of_year % TOTAL_BATCHES) + 1

def load_existing_feed():
    if os.path.exists("deals_feed.json"):
        try:
            with open("deals_feed.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def scrape_brand(brand):
    brand_deals = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        # 15 سیکنڈ کا ٹائم آؤٹ تاکہ 504 ایرر سے بچا جا سکے
        response = requests.get(brand["url"], headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            products = soup.find_all(['div', 'a', 'li'], class_=lambda x: x and any(c in x.lower() for c in ['product', 'card', 'item', 'grid-item']))[:4]
            
            for idx, prod in enumerate(products):
                title_elem = prod.find(['h2', 'h3', 'span', 'a'])
                if title_elem and title_elem.text.strip():
                    title_text = title_elem.text.strip()[:65] + "..."
                    expiry = datetime.now().strftime('%Y-%m-%d')
                    
                    brand_deals.append({
                        "id": f"{brand['id']}_{idx}_{datetime.now().strftime('%y%m%d')}",
                        "shopName": brand["name"],
                        "title": title_text,
                        "category": brand["category"],
                        "city": "All Pakistan",
                        "badge": "SALE",
                        "url": brand["url"],
                        "expiryDate": expiry
                    })
    except Exception as e:
        print(f"Skipping {brand['name']} due to timeout/error: {e}")
    
    return brand_deals

if __name__ == "__main__":
    today_batch = get_today_batch()
    print(f"Today's active Batch for scraping: {today_batch}")
    
    existing_deals = load_existing_feed()
    
    active_deals = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    for deal in existing_deals:
        if deal.get("expiryDate", today_str) >= today_str:
            active_deals.append(deal)
            
    brands_to_scrape = [b for b in ALL_BRANDS if b["batch"] == today_batch]
    
    for brand in brands_to_scrape:
        print(f"Scraping -> {brand['name']} ({brand['category']})...")
        new_items = scrape_brand(brand)
        if new_items:
            active_deals = [d for d in active_deals if d["shopName"] != brand["name"]]
            active_deals.extend(new_items)

    with open("deals_feed.json", "w", encoding="utf-8") as f:
        json.dump(active_deals, f, indent=4, ensure_ascii=False)
        
    print(f"Batch {today_batch} completed. Total active deals in feed: {len(active_deals)}")
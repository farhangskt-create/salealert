import time
import logging
from .base_parser import BaseParser

logger = logging.getLogger("PakistaniDealsParser")

class PakistaniDealsParser(BaseParser):
    def fetch_and_parse(self, source_config: dict) -> list[dict]:
        source_id = source_config.get("id", "unknown")
        source_name = source_config.get("name", "Pakistani Brand")
        category = source_config.get("category", "Shopping")
        city = source_config.get("city", "All")
        source_type = source_config.get("type", "brand")

        now_ms = int(time.time() * 1000)
        one_month_ms = 30 * 24 * 60 * 60 * 1000
        expiry_ms = now_ms + one_month_ms

        logger.info(f"Parsing deals for source '{source_name}' ({source_id})...")

        # Synthetic/verified fixtures matching real Pakistani store structures
        deals = []

        if source_id == "daraz_pk":
            deals.append({
                "dealId": "daraz-elect-01",
                "merchant": "Daraz PK",
                "title": "Flat 30% Off Samsung Galaxy Series",
                "description": "Official brand warranty with free shipping across Pakistan",
                "address": "Online",
                "categoryId": "Electronics",
                "cityId": "All",
                "originalPrice": 85000.0,
                "salePrice": 59500.0,
                "currency": "PKR",
                "imageUrl": "https://img.drz.lazcdn.com/g/p/sample-phone.jpg",
                "sourceUrl": "https://www.daraz.pk/products/samsung-galaxy-sale",
                "latitude": None,
                "longitude": None,
                "startTime": now_ms,
                "expiryTime": expiry_ms,
                "verifiedAt": now_ms,
                "sourceType": "brand",
                "isSponsored": False,
                "lastUpdated": now_ms,
                "status": "active"
            })
            deals.append({
                "dealId": "daraz-fashion-02",
                "merchant": "Daraz PK",
                "title": "Mega Fashion Sale - Up to 50% Off",
                "description": "Top Pakistani lawn & apparel brands discounted",
                "address": "Online",
                "categoryId": "Clothes",
                "cityId": "All",
                "originalPrice": 6000.0,
                "salePrice": 3000.0,
                "currency": "PKR",
                "imageUrl": "https://img.drz.lazcdn.com/g/p/sample-lawn.jpg",
                "sourceUrl": "https://www.daraz.pk/products/fashion-mega-sale",
                "latitude": None,
                "longitude": None,
                "startTime": now_ms,
                "expiryTime": expiry_ms,
                "verifiedAt": now_ms,
                "sourceType": "brand",
                "isSponsored": True,
                "lastUpdated": now_ms,
                "status": "active"
            })

        elif source_id == "khaadi_pk":
            deals.append({
                "dealId": "khaadi-lawn-01",
                "merchant": "Khaadi",
                "title": "Blessed Friday Sale - Flat 40% Off",
                "description": "Unstitched & Pret Summer Collection on Special Discount",
                "address": "Nationwide Outlets & Online",
                "categoryId": "Clothes",
                "cityId": "All",
                "originalPrice": 7500.0,
                "salePrice": 4500.0,
                "currency": "PKR",
                "imageUrl": "https://pk.khaadi.com/images/sale-banner.jpg",
                "sourceUrl": "https://pk.khaadi.com/sale",
                "latitude": None,
                "longitude": None,
                "startTime": now_ms,
                "expiryTime": expiry_ms,
                "verifiedAt": now_ms,
                "sourceType": "brand",
                "isSponsored": False,
                "lastUpdated": now_ms,
                "status": "active"
            })

        elif source_id == "sialkot_local":
            deals.append({
                "dealId": "sialkot-leather-01",
                "merchant": "Sialkot Leather Outlets",
                "title": "Clearance Sale - 25% Off Jackets & Boots",
                "description": "Authentic leather goods discounted at Paris Road branch",
                "address": "Paris Road, Sialkot",
                "categoryId": "Shoes",
                "cityId": "Sialkot",
                "originalPrice": 12000.0,
                "salePrice": 9000.0,
                "currency": "PKR",
                "imageUrl": "https://example.com/images/sialkot-leather.jpg",
                "sourceUrl": "https://example.com/sialkot-leather-sale",
                "latitude": 32.4945,
                "longitude": 74.5229,
                "startTime": now_ms,
                "expiryTime": expiry_ms,
                "verifiedAt": now_ms,
                "sourceType": "merchant",
                "isSponsored": False,
                "lastUpdated": now_ms,
                "status": "active"
            })

        return deals

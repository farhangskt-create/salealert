import time
import logging

logger = logging.getLogger("DealValidator")

ALLOWED_SOURCE_TYPES = {"merchant", "brand", "publisher", "affiliate"}
ALLOWED_STATUSES = {"active", "pending", "rejected", "expired"}
ALLOWED_CURRENCIES = {"PKR", "USD", "EUR", "GBP", "AED", "SAR"}

class DealValidator:
    @staticmethod
    def validate_deal(deal: dict) -> tuple[bool, str]:
        """
        Validates a single deal dictionary against Android StaticDealsSyncWorker rules.
        Returns (is_valid, error_reason).
        """
        deal_id = str(deal.get("dealId", "")).strip()
        merchant = str(deal.get("merchant", "")).strip()
        title = str(deal.get("title", "")).strip()
        category_id = str(deal.get("categoryId", "")).strip()
        source_type = str(deal.get("sourceType", "brand")).strip()
        status = str(deal.get("status", "active")).strip()

        if not deal_id:
            return False, "Missing or blank dealId"
        if not merchant:
            return False, f"Deal {deal_id}: Missing or blank merchant"
        if not title:
            return False, f"Deal {deal_id}: Missing or blank title"
        if not category_id:
            return False, f"Deal {deal_id}: Missing or blank categoryId"
        if source_type not in ALLOWED_SOURCE_TYPES:
            return False, f"Deal {deal_id}: Unsupported sourceType '{source_type}'"
        if status not in ALLOWED_STATUSES:
            return False, f"Deal {deal_id}: Unsupported status '{status}'"

        orig_price = deal.get("originalPrice")
        sale_price = deal.get("salePrice")

        if (orig_price is None) != (sale_price is None):
            return False, f"Deal {deal_id}: Must provide both originalPrice and salePrice or neither"

        if orig_price is not None and sale_price is not None:
            try:
                op = float(orig_price)
                sp = float(sale_price)
                if op <= sp or sp <= 0.0:
                    return False, f"Deal {deal_id}: Inconsistent prices (original={op}, sale={sp})"
            except (ValueError, TypeError):
                return False, f"Deal {deal_id}: Non-numeric price values"

            currency = str(deal.get("currency", "")).strip()
            if not currency or currency not in ALLOWED_CURRENCIES:
                return False, f"Deal {deal_id}: Invalid or missing currency '{currency}'"

        now_ms = int(time.time() * 1000)
        expiry_time = deal.get("expiryTime")
        if expiry_time is not None:
            try:
                exp_ms = int(expiry_time)
                if exp_ms <= now_ms:
                    return False, f"Deal {deal_id}: Expired deal (expiryTime={exp_ms} <= now={now_ms})"
            except (ValueError, TypeError):
                return False, f"Deal {deal_id}: Invalid expiryTime format"

        last_updated = deal.get("lastUpdated")
        if last_updated is None:
            return False, f"Deal {deal_id}: Missing mandatory lastUpdated timestamp"

        return True, ""

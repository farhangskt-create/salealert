import logging

logger = logging.getLogger("AdminApprovalQueue")

class AdminApprovalQueue:
    def __init__(self):
        self.pending_queue: list[dict] = []
        self.approved_queue: list[dict] = []
        self.rejected_queue: list[dict] = []

    def submit_deal(self, deal: dict):
        status = deal.get("status", "pending")
        if status == "active":
            self.approved_queue.append(deal)
            logger.info(f"Deal '{deal.get('dealId')}' automatically approved (status=active).")
        elif status == "pending":
            self.pending_queue.append(deal)
            logger.info(f"Deal '{deal.get('dealId')}' added to Admin Pending Approval Queue.")
        else:
            self.rejected_queue.append(deal)
            logger.info(f"Deal '{deal.get('dealId')}' added to Rejected Queue (status={status}).")

    def approve_deal(self, deal_id: str) -> bool:
        for idx, deal in enumerate(self.pending_queue):
            if deal.get("dealId") == deal_id:
                deal["status"] = "active"
                approved = self.pending_queue.pop(idx)
                self.approved_queue.append(approved)
                logger.info(f"Admin approved deal '{deal_id}'. Moved to publication queue.")
                return True
        return False

    def reject_deal(self, deal_id: str, reason: str = "") -> bool:
        for idx, deal in enumerate(self.pending_queue):
            if deal.get("dealId") == deal_id:
                deal["status"] = "rejected"
                rejected = self.pending_queue.pop(idx)
                self.rejected_queue.append(rejected)
                logger.info(f"Admin rejected deal '{deal_id}': {reason}")
                return True
        return False

    def get_published_deals(self) -> list[dict]:
        """Returns only active, approved deals ready for publication."""
        return self.approved_queue

    def get_stats(self) -> dict:
        return {
            "pending": len(self.pending_queue),
            "approved": len(self.approved_queue),
            "rejected": len(self.rejected_queue)
        }

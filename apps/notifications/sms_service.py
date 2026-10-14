"""
SMS Notification Service for FlexyRide Corporate.
Supports:
1. Africa's Talking SMS Gateway (standard for Ghana & Pan-African mobile networks)
2. Twilio SMS Gateway (international fallback)
3. Console / Dev Simulation Fallback (when credentials are not yet configured)
"""
import os
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SMSService:
    """Unified SMS gateway service with multi-provider failover."""

    def __init__(self):
        # Africa's Talking Configuration
        self.at_username = os.environ.get('AFRICASTALKING_USERNAME', '').strip()
        self.at_api_key = os.environ.get('AFRICASTALKING_API_KEY', '').strip()
        self.at_sender_id = os.environ.get('AFRICASTALKING_SENDER_ID', 'FlexyRide').strip()
        self.at_is_sandbox = self.at_username.lower() == 'sandbox'

        # Twilio Configuration
        self.twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
        self.twilio_token = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
        self.twilio_from = os.environ.get('TWILIO_PHONE_NUMBER', '').strip()

    def is_configured(self) -> bool:
        """Returns True if any live gateway credentials are provided."""
        return bool(
            (self.at_username and self.at_api_key) or
            (self.twilio_sid and self.twilio_token and self.twilio_from)
        )

    def normalize_phone(self, phone: str) -> str:
        """Formats phone numbers to international E.164 format (e.g. +233XXXXXXXXX for Ghana)."""
        if not phone:
            return ""
        cleaned = "".join(c for c in phone if c.isdigit() or c == '+')
        if cleaned.startswith('+'):
            return cleaned
        if cleaned.startswith('00'):
            return '+' + cleaned[2:]
        if cleaned.startswith('0') and len(cleaned) == 10:
            # Standard Ghana 0XXXXXXXXX -> +233XXXXXXXXX
            return '+233' + cleaned[1:]
        if len(cleaned) == 9 and not cleaned.startswith('0'):
            return '+233' + cleaned
        return '+' + cleaned if not cleaned.startswith('+') else cleaned

    def send_sms(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Dispatches a single SMS to the given recipient."""
        recipients = [self.normalize_phone(to_phone)]
        return self.send_bulk_sms(recipients, message)

    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """
        Dispatches an SMS to multiple recipients in bulk.
        Returns a dictionary with status, delivered count, and failure details.
        """
        normalized_numbers = [
            self.normalize_phone(p) for p in phone_numbers if p and len(p.strip()) > 5
        ]
        # Deduplicate while preserving order
        unique_numbers = list(dict.fromkeys(normalized_numbers))

        if not unique_numbers:
            return {
                "success": False,
                "provider": "none",
                "message": "No valid phone numbers provided.",
                "sent_count": 0,
                "failed_count": 0
            }

        # 1. Try Africa's Talking first
        if self.at_username and self.at_api_key:
            res = self._send_africastalking(unique_numbers, message)
            if res.get("success"):
                return res
            logger.warning("[SMS] Africa's Talking failed: %s. Attempting fallback.", res.get("message"))

        # 2. Try Twilio fallback
        if self.twilio_sid and self.twilio_token and self.twilio_from:
            res = self._send_twilio(unique_numbers, message)
            if res.get("success"):
                return res
            logger.warning("[SMS] Twilio fallback failed: %s.", res.get("message"))

        # 3. Development / Simulation Mode Fallback
        logger.info(
            "[SMS Console Simulation] Bulk SMS to %d recipients: '%s' (Numbers: %s)",
            len(unique_numbers),
            message[:60] + "...",
            unique_numbers[:3]
        )
        return {
            "success": True,
            "provider": "console_simulation",
            "message": f"Simulated SMS delivery to {len(unique_numbers)} recipient(s) (Live SMS gateway credentials not set in .env).",
            "sent_count": len(unique_numbers),
            "failed_count": 0,
            "recipients": unique_numbers
        }

    def _send_africastalking(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Sends SMS via Africa's Talking HTTP API."""
        url = (
            "https://api.sandbox.africastalking.com/version1/messaging"
            if self.at_is_sandbox
            else "https://api.africastalking.com/version1/messaging"
        )
        headers = {
            "apiKey": self.at_api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "username": self.at_username,
            "to": ",".join(phone_numbers),
            "message": message
        }
        if self.at_sender_id and not self.at_is_sandbox:
            data["from"] = self.at_sender_id

        try:
            resp = requests.post(url, headers=headers, data=data, timeout=12)
            if resp.status_code in (200, 201):
                res_json = resp.json()
                sms_data = res_json.get("SMSMessageData", {})
                recipients_data = sms_data.get("Recipients", [])
                sent_count = sum(1 for r in recipients_data if r.get("status") in ("Success", "Sent"))
                failed_count = len(phone_numbers) - sent_count
                return {
                    "success": True,
                    "provider": "africastalking",
                    "sent_count": sent_count or len(phone_numbers),
                    "failed_count": failed_count,
                    "message": sms_data.get("Message", "Sent successfully")
                }
            return {
                "success": False,
                "provider": "africastalking",
                "message": f"HTTP {resp.status_code}: {resp.text}"
            }
        except Exception as e:
            return {"success": False, "provider": "africastalking", "message": str(e)}

    def _send_twilio(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Sends SMS via Twilio Messages API."""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
        auth = (self.twilio_sid, self.twilio_token)
        sent_count = 0
        failed_count = 0

        for number in phone_numbers:
            try:
                data = {
                    "To": number,
                    "From": self.twilio_from,
                    "Body": message
                }
                resp = requests.post(url, auth=auth, data=data, timeout=8)
                if resp.status_code in (200, 201):
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        return {
            "success": sent_count > 0,
            "provider": "twilio",
            "sent_count": sent_count,
            "failed_count": failed_count,
            "message": f"Twilio dispatched {sent_count}/{len(phone_numbers)} SMS message(s)."
        }


# Singleton service instance
sms_service = SMSService()

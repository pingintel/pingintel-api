import hashlib
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac

class UrlSignatureFactory:
    def __init__(self, secret):
        self.secret = str(secret)

    def generate(self, user_id: str | int =0, expiration: timedelta=timedelta(minutes=20)):
        expires = datetime.now(timezone.utc) + expiration
        expires_at = self._generate_timestamp(expires)
        return self._makesig(user_id, expires_at), expires_at

    def is_valid(self, signature: str, expires_at: int, user_id: str | int = 0):
        expected_signature = self._makesig(user_id, expires_at)
        
        if not hmac.compare_digest(expected_signature, signature):
            return False

        if int(expires_at) < self._generate_timestamp(datetime.now(timezone.utc)):
            return False

        return True

    def _makesig(self, user_id: str | int, expires_at: int):
        signature = hmac.new(self.secret.encode("utf-8"), (str(user_id) + str(expires_at)).encode("utf-8"), hashlib.sha256).hexdigest()

        return signature

    @classmethod
    def _generate_timestamp(cls, when) -> int:
        def totimestamp(dt, epoch=datetime(1970, 1, 1)):
            td = dt.replace(tzinfo=None) - epoch.replace(tzinfo=None)
            return (
                td.microseconds + (td.seconds + td.days * 86_400) * 1_000_000
            ) / 1_000_000

        return int(round(totimestamp(when)))
import hashlib
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac

class UrlSignatureFactory:
    def __init__(self, secret):
        self.secret = str(secret)

    def generate(self, user_id=0, expiration=timedelta(minutes=20)):
        expires = datetime.now(timezone.utc) + expiration
        expires_at = self._generate_timestamp(expires)
        return self._makesig(user_id, expires_at)

    def is_valid(self, signature):
        try:
            _, expires_at, user_id = signature.split("-", 3)
        except ValueError:
            return False

        expires_at = int(expires_at)
        expected_signature = self._makesig(user_id, expires_at)
        
        if not hmac.compare_digest(expected_signature, signature):
            return False

        if expires_at < self._generate_timestamp(datetime.now(timezone.utc)):
            return False

        return True

    def _makesig(self, user_id: str | int, expires_at: int):
        signature = base64.urlsafe_b64encode(hmac.new(self.secret, (str(user_id) + str(expires_at)).encode("utf-8"), hashlib.sha256).digest())

        return "PS{}-{}-{}".format(signature, expires_at, user_id)

    @classmethod
    def _generate_timestamp(cls, when) -> int:
        def totimestamp(dt, epoch=datetime(1970, 1, 1)):
            td = dt - epoch
            return (
                td.microseconds + (td.seconds + td.days * 86_400) * 1_000_000
            ) / 1_000_000

        return int(round(totimestamp(when)))
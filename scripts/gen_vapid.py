"""VAPID 키 생성기 — 웹푸시용 공개/비공개 키를 출력.

사용:
  python -m scripts.gen_vapid

출력된 두 값을 .env 에 넣으세요:
  VAPID_PUBLIC_KEY=...
  VAPID_PRIVATE_KEY=...
  VAPID_SUBJECT=mailto:you@example.com   (연락 가능한 메일/URL)

pywebpush 설치 시 함께 들어오는 py_vapid 를 사용합니다.
"""
import sys


def main() -> int:
    try:
        from py_vapid import Vapid01
    except Exception:
        print("py_vapid 가 없습니다. `pip install pywebpush` 후 다시 실행하세요.", file=sys.stderr)
        return 1
    v = Vapid01()
    v.generate_keys()
    # application server key(공개)와 private key를 base64url 로 출력
    pub = v.public_key_urlsafe_base64() if hasattr(v, "public_key_urlsafe_base64") else None
    priv = v.private_key_urlsafe_base64() if hasattr(v, "private_key_urlsafe_base64") else None
    if not pub or not priv:
        # 버전별 API 차이 대응
        from py_vapid import b64urlencode
        from cryptography.hazmat.primitives import serialization
        nums = v.private_key.private_numbers()
        priv = b64urlencode(nums.private_value.to_bytes(32, "big"))
        raw = v.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)
        pub = b64urlencode(raw)
    print("VAPID_PUBLIC_KEY=" + pub)
    print("VAPID_PRIVATE_KEY=" + priv)
    print("VAPID_SUBJECT=mailto:admin@example.com  # 실제 연락처로 변경")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

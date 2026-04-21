import os
import base64

def generate_fernet_key() -> str:
    # 32 url-safe random bytes, base64-urlsafe-encoded (Fernet key format)
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

if __name__ == '__main__':
    key = generate_fernet_key()
    print(key)
    print()
    print("Add the following line to your .env file:")
    print(f"TOKEN_ENCRYPTION_KEY={key}")

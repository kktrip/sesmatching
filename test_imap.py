"""
IMAP / POP3接続デバッグスクリプト
実行: python3 test_imap.py
"""
import imaplib
import poplib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("IMAP_HOST", "irohamaru-works.sakura.ne.jp")
USER_FULL = os.getenv("IMAP_USER", "")
USER_SHORT = USER_FULL.split("@")[0] if USER_FULL else ""
USER_SAKURA = USER_FULL
PASSWORD = os.getenv("IMAP_PASSWORD", "")


def imap_auth_plain(host, port, user, password, use_ssl=True):
    """AUTH=PLAINで認証を試みる"""
    try:
        conn = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
        if not use_ssl:
            conn.starttls()
        auth_str = f"\x00{user}\x00{password}"
        encoded = base64.b64encode(auth_str.encode()).decode()
        typ, data = conn.authenticate("PLAIN", lambda x: encoded.encode())
        if typ == "OK":
            print(f"  [OK] AUTH=PLAIN成功 [user={user}]")
            conn.logout()
            return True
        else:
            print(f"  [NG] AUTH=PLAIN失敗 [user={user}]: {data}")
            return False
    except Exception as e:
        print(f"  [NG] AUTH=PLAINエラー [user={user}]: {e}")
        return False


print("=" * 50)
print("メールサーバー接続デバッグ")
print("=" * 50)

# 1. IMAP SSL (port 993) - LOGIN
print("\n[1] IMAP SSL port 993 - LOGIN")
try:
    conn = imaplib.IMAP4_SSL(HOST, 993)
    print("  接続: OK")
    for user in [USER_FULL, USER_SHORT, USER_SAKURA]:
        try:
            c = imaplib.IMAP4_SSL(HOST, 993)
            c.login(user, PASSWORD)
            print(f"  [OK] ログイン成功 [user={user}]")
            c.logout()
            break
        except imaplib.IMAP4.error as e:
            print(f"  [NG] ログイン失敗 [user={user}]: {e}")
except Exception as e:
    print(f"  接続失敗: {e}")

# 2. IMAP SSL (port 993) - AUTH=PLAIN
print("\n[2] IMAP SSL port 993 - AUTH=PLAIN")
for user in [USER_FULL, USER_SHORT, USER_SAKURA]:
    if imap_auth_plain(HOST, 993, user, PASSWORD, use_ssl=True):
        break

# 3. IMAP STARTTLS (port 143) - AUTH=PLAIN
print("\n[3] IMAP STARTTLS port 143 - AUTH=PLAIN")
for user in [USER_FULL, USER_SHORT, USER_SAKURA]:
    if imap_auth_plain(HOST, 143, user, PASSWORD, use_ssl=False):
        break

# 4. POP3 SSL (port 995)
print("\n[4] POP3 SSL port 995")
try:
    pop = poplib.POP3_SSL(HOST, 995)
    print("  接続: OK")
    for user in [USER_FULL, USER_SHORT, USER_SAKURA]:
        try:
            pop2 = poplib.POP3_SSL(HOST, 995)
            pop2.user(user)
            pop2.pass_(PASSWORD)
            count, size = pop2.stat()
            print(f"  [OK] ログイン成功 [user={user}] メール数: {count}")
            pop2.quit()
            break
        except poplib.error_proto as e:
            print(f"  [NG] ログイン失敗 [user={user}]: {e}")
except Exception as e:
    print(f"  接続失敗: {e}")

# 5. POP3 (port 110)
print("\n[5] POP3 port 110")
try:
    pop = poplib.POP3(HOST, 110)
    print("  接続: OK")
    for user in [USER_FULL, USER_SHORT, USER_SAKURA]:
        try:
            pop2 = poplib.POP3(HOST, 110)
            pop2.user(user)
            pop2.pass_(PASSWORD)
            count, size = pop2.stat()
            print(f"  [OK] ログイン成功 [user={user}] メール数: {count}")
            pop2.quit()
            break
        except poplib.error_proto as e:
            print(f"  [NG] ログイン失敗 [user={user}]: {e}")
except Exception as e:
    print(f"  接続失敗: {e}")

print("\n" + "=" * 50)

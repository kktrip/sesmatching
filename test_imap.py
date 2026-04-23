"""
IMAP接続デバッグスクリプト
実行: python3 test_imap.py
"""
import imaplib
import ssl

HOST = "www764.sakura.ne.jp"
PORT_SSL = 993
PORT_STARTTLS = 143
USER_FULL = "info@falcs.jp"
USER_SHORT = "info"
PASSWORD = "pC5SWv3tp9U5"


def try_login(conn, user, password, label):
    try:
        conn.login(user, password)
        print(f"  ✅ ログイン成功 [{label}]")
        conn.logout()
        return True
    except imaplib.IMAP4.error as e:
        print(f"  ❌ ログイン失敗 [{label}]: {e}")
        return False


print("=" * 50)
print("IMAP接続デバッグ")
print("=" * 50)

# 1. SSL (port 993)
print(f"\n[1] SSL接続 (port {PORT_SSL})")
try:
    conn = imaplib.IMAP4_SSL(HOST, PORT_SSL)
    print("  接続: OK")
    cap = conn.capability()
    print(f"  Capability: {cap[1]}")
    for user in [USER_FULL, USER_SHORT]:
        c = imaplib.IMAP4_SSL(HOST, PORT_SSL)
        if try_login(c, user, PASSWORD, f"user={user}"):
            break
except Exception as e:
    print(f"  接続失敗: {type(e).__name__}: {e}")

# 2. STARTTLS (port 143)
print(f"\n[2] STARTTLS接続 (port {PORT_STARTTLS})")
try:
    conn = imaplib.IMAP4(HOST, PORT_STARTTLS)
    conn.starttls()
    print("  接続: OK")
    for user in [USER_FULL, USER_SHORT]:
        c = imaplib.IMAP4(HOST, PORT_STARTTLS)
        c.starttls()
        if try_login(c, user, PASSWORD, f"user={user}"):
            break
except Exception as e:
    print(f"  接続失敗: {type(e).__name__}: {e}")

print("\n" + "=" * 50)

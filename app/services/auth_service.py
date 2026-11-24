"""Auth service: password hashing (and, later, JWT login tokens).

We never store a user's real password. Instead we store a *hash*: the result
of running the password through a one-way function. At login we hash the
password the user typed in the same way and compare the two results.

We use scrypt, which is built into Python's hashlib (decided in issue #9, so
no extra dependency is needed). scrypt is deliberately slow and uses a lot of
memory, so guessing passwords by brute force is expensive.

A random "salt" is mixed in for every password, so two users with the same
password still get different hashes.

A stored hash looks like this (one line, split by "$"):

    scrypt$32768$8$1$<salt in base64>$<hash in base64>
    ^name  ^n    ^r ^p

Storing n, r and p next to the hash means we can make hashing stronger later
without breaking passwords that were already saved.
"""

import base64
import hashlib
import hmac
import secrets

# ---------- Settings ----------
# n = CPU/memory cost, r = block size, p = parallelism. Memory used is about
# 128 * n * r bytes, so these values use 32 MiB per hash.
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
HASH_BYTES = 32

# verify_password reads n, r and p back out of the stored hash. A broken or
# tampered hash could ask for huge values and keep the server busy for
# seconds or minutes, so we only accept a safe range: n may be raised later
# (up to 2**17), while r and p must stay at the values above.
MIN_N = 2**14
MAX_N = 2**17
# hashlib refuses to use more than 32 MiB unless we raise the limit. This is
# enough for MAX_N (128 MiB); today's settings only use 32 MiB.
MAX_MEMORY = 256 * 1024 * 1024

PREFIX = "scrypt"


def _scrypt(plain: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        plain.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=MAX_MEMORY, dklen=HASH_BYTES,
    )


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(plain: str) -> str:
    """Turn a password into a salted hash that is safe to store in User.password_hash.

    Password rules (e.g. minimum length) are not checked here; the
    registration route will do that later (decided in issue #9).
    """
    salt = secrets.token_bytes(SALT_BYTES)  # a new random salt every time
    digest = _scrypt(plain, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"{PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(plain: str, stored_hash: str) -> bool:
    """Return True if plain is the password that stored_hash was made from.

    Returns False (instead of crashing) if stored_hash isn't in our format,
    for example an old plain-text value, or if its settings are outside the
    safe range above.
    """
    if not isinstance(stored_hash, str):
        return False
    try:
        prefix, n_text, r_text, p_text, salt_b64, digest_b64 = stored_hash.split("$")
        n, r, p = int(n_text), int(r_text), int(p_text)
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(digest_b64, validate=True)
    except ValueError:
        # Wrong number of parts, n/r/p not whole numbers, or bad base64.
        return False

    # Check everything cheap *before* doing the expensive scrypt work.
    if prefix != PREFIX or len(expected) != HASH_BYTES:
        return False
    if not MIN_N <= n <= MAX_N or r != SCRYPT_R or p != SCRYPT_P:
        return False

    try:
        actual = _scrypt(plain, salt, n, r, p)
    except ValueError:
        # e.g. n is not a power of 2, or the password can't be encoded.
        return False
    # compare_digest takes the same time whether the first byte or the last
    # byte differs, so an attacker can't learn the hash by timing us.
    return hmac.compare_digest(actual, expected)

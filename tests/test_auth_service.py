import base64
import hashlib
import json
import os
import time

import pytest

from app.config import DATA_DIR
from app.services.auth_service import hash_password, verify_password


# ---------- hash_password ----------

def test_hash_is_not_the_plain_password():
    stored = hash_password("correct horse")

    assert "correct horse" not in stored
    assert stored.startswith("scrypt$")


def test_same_password_gives_different_hashes():
    # A new random salt is used each time.
    assert hash_password("secret") != hash_password("secret")


# ---------- verify_password ----------

def test_right_password_verifies():
    stored = hash_password("secret")

    assert verify_password("secret", stored) is True


def test_wrong_password_does_not_verify():
    stored = hash_password("secret")

    assert verify_password("Secret", stored) is False
    assert verify_password("", stored) is False


def test_empty_and_unicode_passwords_work():
    assert verify_password("", hash_password("")) is True
    assert verify_password("pässwörd♞", hash_password("pässwörd♞")) is True


def test_changed_hash_does_not_verify():
    stored = hash_password("secret")
    prefix, n, r, p, salt, digest = stored.split("$")
    other_digest = hash_password("other").split("$")[-1]

    assert verify_password("secret", "$".join([prefix, n, r, p, salt, other_digest])) is False


@pytest.mark.parametrize(
    "stored",
    [
        "1234",                                   # old plain-text value
        "",
        "scrypt$32768$8$1$onlyfiveparts",
        "bcrypt$32768$8$1$AAAA$AAAA",             # unknown algorithm name
        "scrypt$abc$8$1$AAAA$AAAA",               # n is not a number
        "scrypt$3$8$1$AAAA$AAAA",                 # n must be a power of 2
        "scrypt$32768$8$1$not*base64$AAAA",
        f"scrypt${2**80}$8$1$AAAA$AAAA",          # far too big for scrypt
        f"scrypt${2**30}$8$1$AAAA$AAAA",          # would need too much memory
    ],
)
def test_malformed_stored_hash_returns_false(stored):
    assert verify_password("1234", stored) is False


def test_non_string_stored_hash_returns_false():
    assert verify_password("1234", None) is False


def with_settings(stored, n=None, r=None, p=None, digest=None):
    """Return stored with some of its parts swapped out."""
    prefix, old_n, old_r, old_p, salt, old_digest = stored.split("$")
    parts = [prefix, n or old_n, r or old_r, p or old_p, salt, digest or old_digest]
    return "$".join(str(part) for part in parts)


@pytest.mark.parametrize(
    "changes",
    [
        {"p": 100000},     # huge p: would keep the CPU busy for many seconds
        {"r": 1},          # r must stay at 8
        {"r": 64},
        {"p": 2},          # p must stay at 1
        {"n": 2**13},      # below the minimum strength
        {"n": 2**18},      # above the maximum we allow
        {"n": 2**14 + 1},  # in range but not a power of 2
        {"digest": "AAAA"},  # digest has the wrong length
    ],
)
def test_stored_settings_outside_safe_range_return_false_quickly(changes):
    stored = with_settings(hash_password("secret"), **changes)

    start = time.perf_counter()
    assert verify_password("secret", stored) is False
    assert time.perf_counter() - start < 1


def test_hash_made_with_other_allowed_n_still_verifies():
    """Old hashes keep working if SCRYPT_N is changed later (within the safe range)."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(b"secret", salt=salt, n=2**14, r=8, p=1, dklen=32)
    stored = "$".join(
        ["scrypt", str(2**14), "8", "1",
         base64.b64encode(salt).decode(), base64.b64encode(digest).decode()]
    )

    assert verify_password("secret", stored) is True
    assert verify_password("wrong", stored) is False


# ---------- Sample data ----------

def test_sample_users_have_hashed_passwords():
    """The sample users in data/users.json still log in with their old passwords."""
    users = json.loads((DATA_DIR / "users.json").read_text(encoding="utf-8"))
    passwords = {"Abdul138": "1234", "Magnus": "4567"}

    for user in users:
        assert user["password_hash"] != passwords[user["username"]]
        assert verify_password(passwords[user["username"]], user["password_hash"])

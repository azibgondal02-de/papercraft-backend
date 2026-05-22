from argon2 import PasswordHasher, exceptions

# Create a hasher with sensible defaults (argon2id, memory/time parallelism tuned)
ph = PasswordHasher(
    time_cost=3,  # iterations (increase for more CPU)
    memory_cost=64 * 1024,  # memory in kibibytes (64 MiB)
    parallelism=4,  # CPU threads
    hash_len=32,  # length of produced hash in bytes
)


def hash_password(plain_password: str) -> str:
    """
    Returns a string containing all info needed to verify (hash + parameters),
    safe to store directly in your DB.
    """
    return ph.hash(plain_password)

print(hash_password("1234"))

def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """
    Returns True if candidate_password matches stored_hash, False otherwise.
    """
    try:
        return ph.verify(stored_hash, candidate_password)
    except exceptions.VerifyMismatchError:
        return False
    except exceptions.VerificationError:
        # Other verification problems (corrupt hash) — treat as failure
        return False



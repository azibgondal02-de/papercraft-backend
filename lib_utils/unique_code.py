import uuid


def generate_unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

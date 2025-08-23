import uuid

def generate_reference():
    return f"TXN-{uuid.uuid4().hex[:10].upper()}"


def generate_remmittance_reference():
    return f"RMT-{uuid.uuid4().hex[:10].upper()}"
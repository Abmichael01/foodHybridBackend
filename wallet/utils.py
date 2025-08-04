import uuid

def generate_reference():
    return f"TXN-{uuid.uuid4().hex[:10].upper()}"
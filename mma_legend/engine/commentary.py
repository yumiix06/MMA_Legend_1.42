def describe(event) -> str:
    return getattr(event, "text", "") or str(event)

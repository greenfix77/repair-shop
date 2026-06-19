def search_repairs(repairs: list, text: str) -> list:
    """Return matching repair indices"""
    text = text.lower()
    matching = []

    for i, r in enumerate(repairs):
        if (
            text in str(r.get("customer_name", "")).lower()
            or text in str(r.get("phone", "")).lower()
            or text in str(r.get("brand", "")).lower()
            or text in str(r.get("model", "")).lower()
            or text in str(r.get("issue", "")).lower()
        ):
            matching.append(i)

    return matching


def filter_repairs(repairs: list, status: str) -> list:
    """Return matching repair indices by status"""
    matching = []

    for i, r in enumerate(repairs):
        if status == "همه" or r.get("status") == status:
            matching.append(i)

    return matching
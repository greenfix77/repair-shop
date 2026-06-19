from core.status import STATUS_COLORS, DEFAULT_STATUS_COLOR


def get_status_color(status: str) -> str:
    return STATUS_COLORS.get(status, DEFAULT_STATUS_COLOR)

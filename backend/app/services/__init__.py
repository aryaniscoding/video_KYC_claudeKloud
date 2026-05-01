def _find_recommended_tenure(preferred: int | None, options: list[int]) -> int:
    if not preferred or not options:
        return options[1] if len(options) > 1 else options[0]
    return min(options, key=lambda t: abs(t - preferred))

class InvalidFormatException(Exception):
    pass

def check_gecko_profile(prof):
    if "meta" not in prof:
        raise InvalidFormatException("meta key missing")


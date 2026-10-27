"""Supported project formats; frame rate stays fixed at 24 fps."""
FORMATS = {'portrait': (1080, 1920), 'widescreen': (1920, 1080)}
LABELS = {'portrait': 'Portrait 9:16', 'widescreen': 'Widescreen 16:9'}


def format_value(value):
    if not isinstance(value, str) or value not in FORMATS:
        raise ValueError('Choose portrait or widescreen project format')
    return value


def output_size(value='portrait'):
    return FORMATS[format_value(value)]

"""Section trims, transitions and the exact frame plan the exporter follows.

Everything is whole frames at 24 fps, so the on-screen timeline, titles/audio times and the
finished MP4 agree to the frame.

Per section (all optional, old timelines are unchanged):
  trim_in / trim_out  frames removed from the start / kept up to (source frame numbers)
  transition          {'kind': 'dissolve' | 'fade', 'frames': 2..96} between the previous section and this one
    dissolve  the two sections overlap and cross-fade; total length shrinks by `frames`
    fade      dip to black: previous section fades out and this one fades in over `frames` each; length unchanged
"""
KINDS = ('dissolve', 'fade')
MAX_TRANSITION = 96


def _frames(value, label, low=0):
    if type(value) is not int or value < low:
        raise ValueError(f'{label} must be a whole number of frames, at least {low}')
    return value


def validate_edit(section):
    """Structural check of a section's trim/transition fields (no source access)."""
    if 'trim_in' in section:
        _frames(section['trim_in'], 'Trim start')
    if 'trim_out' in section:
        _frames(section['trim_out'], 'Trim end', 1)
        if section['trim_out'] <= section.get('trim_in', 0):
            raise ValueError('Trim end must be after trim start')
    transition = section.get('transition')
    if transition is not None:
        if not isinstance(transition, dict) or set(transition) - {'kind', 'frames'} or transition.get('kind') not in KINDS:
            raise ValueError('Transition must be dissolve or fade')
        frames = transition.get('frames')
        if type(frames) is not int or not 2 <= frames <= MAX_TRANSITION:
            raise ValueError(f'Transition must last 2–{MAX_TRANSITION} frames')


def window(section, source_frames):
    """(first, end) source frames kept for a section; raises when the source no longer covers the trim."""
    first = section.get('trim_in', 0)
    end = section.get('trim_out', source_frames)
    if end > source_frames:
        raise ValueError(f'“{section["name"]}” is trimmed to frame {end} but its source now has only {source_frames} frames')
    if first >= end:
        raise ValueError(f'“{section["name"]}” has no frames left after trimming')
    return first, end


def plan(sections, source_frames):
    """Exact export plan.

    Returns dict(total, starts, lengths, overlaps, fades, parts):
      lengths[i]  frames of section i after trimming
      overlaps[i] dissolve frames shared with section i-1 (0 for cut/fade/first)
      fades[i]    (fade_in, fade_out) frames of dip-to-black inside section i
      starts[i]   timeline frame where section i begins
      parts       ordered clips: ('main', i, first, end, fade_in, fade_out) | ('mix', i, frames) joining i-1 into i
    """
    count = len(sections)
    spans = [window(s, n) for s, n in zip(sections, source_frames)]
    lengths = [end-first for first, end in spans]
    overlaps, fades = [0]*count, [[0, 0] for _ in range(count)]
    for i in range(1, count):
        transition = sections[i].get('transition')
        if not transition:
            continue
        frames = transition['frames']
        if frames > min(lengths[i-1], lengths[i]):
            raise ValueError(f'The {transition["kind"]} into “{sections[i]["name"]}” is longer than a neighbouring section')
        if transition['kind'] == 'dissolve':
            overlaps[i] = frames
        else:
            fades[i-1][1] = frames
            fades[i][0] = frames
    starts, cursor = [], 0
    for i in range(count):
        cursor -= overlaps[i]
        starts.append(cursor)
        cursor += lengths[i]
    parts = []
    for i in range(count):
        head, tail = overlaps[i], overlaps[i+1] if i+1 < count else 0
        keep = lengths[i]-head-tail
        if keep < 0:
            raise ValueError(f'“{sections[i]["name"]}” is too short for the transitions on both sides')
        if fades[i][0]+fades[i][1] > lengths[i]:
            raise ValueError(f'“{sections[i]["name"]}” is too short for the fades on both sides')
        if i and overlaps[i]:
            parts.append(('mix', i, overlaps[i]))
        if keep:
            parts.append(('main', i, spans[i][0]+head, spans[i][1]-tail, fades[i][0], fades[i][1]))
    return dict(total=cursor, starts=starts, lengths=lengths, overlaps=overlaps, fades=[tuple(f) for f in fades], parts=parts, spans=spans)


def split(section, at_frame, source_frames):
    """Split one section at ``at_frame`` frames from its (trimmed) start; returns two new section dicts."""
    first, end = window(section, source_frames)
    if not 0 < at_frame < end-first:
        raise ValueError('Split inside the section, not at its very start or end')
    left, right = dict(section), dict(section)
    left['trim_in'], left['trim_out'] = first, first+at_frame
    right['trim_in'], right['trim_out'] = first+at_frame, end
    right.pop('transition', None)           # the cut between the two halves is a plain cut
    left['name'] = section['name'][:92]+' · 1'
    right['name'] = section['name'][:92]+' · 2'
    if first == 0:
        left.pop('trim_in')
    if end == source_frames:
        right.pop('trim_out')
    return left, right

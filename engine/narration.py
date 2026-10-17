"""Offline narration using the existing local Kokoro model and voice bank."""
import json
import os
import time
import uuid
from pathlib import Path


def generate(text, output, voice="am_michael", speed=1.0):
    from kokoro_onnx import Kokoro
    from phonemes import phonemize
    import soundfile as sf
    text = text.strip()
    if not text or len(text) > 10000:
        raise ValueError("Enter 1–10,000 characters of narration")
    speed = float(speed)
    if not .5 <= speed <= 2:
        raise ValueError("Speed must be 0.5–2")
    root = Path(os.environ.get("STORY_STUDIO", Path(__file__).resolve().parents[1])).resolve()
    model_root = Path(os.environ.get("STORY_STUDIO_MODEL_ROOT", root / "models" / "kokoro"))
    output = Path(output).resolve()
    if not output.is_relative_to(root):
        raise ValueError("Narration output must stay inside StoryStudio")
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError("Choose a new narration filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    engine = Kokoro(str(model_root / "kokoro-v1.0.int8.onnx"), str(model_root / "voices-v1.0.bin"))
    pronunciation = engine.tokenizer.known(phonemize(text))
    samples, rate = engine.create(pronunciation, voice=voice, speed=speed, lang="en-us", is_phonemes=True)
    temporary = output.with_name(output.stem + "." + uuid.uuid4().hex + ".wav")
    try:
        sf.write(str(temporary), samples, rate, subtype="PCM_16")
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    metadata = {"output": str(output), "duration_seconds": len(samples)/rate,
                "sample_rate": rate, "voice": voice, "generation_seconds": round(time.monotonic()-start, 2),
                "provider": "local Kokoro ONNX"}
    with output.with_suffix(".json").open("x", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    return metadata

"""Offline narration. All model paths are explicit and live under StoryStudio."""
from pathlib import Path
import argparse,json,time
import soundfile as sf
from kokoro_onnx import Kokoro
from phonemes import phonemize

ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description='Generate local narration without an API key')
 p.add_argument('text',help='Text or a UTF-8 .txt file')
 p.add_argument('--output',type=Path,default=ROOT/'exports/narration.wav')
 p.add_argument('--voice',default='am_michael')
 p.add_argument('--speed',type=float,default=1.0)
 args=p.parse_args()
 path=Path(args.text)
 text=path.read_text(encoding='utf8') if len(args.text)<240 and path.is_file() else args.text
 if not .5<=args.speed<=2: p.error('Speed must be between 0.5 and 2')
 dest=args.output.resolve()
 if not dest.is_relative_to(ROOT.resolve()):p.error('Output must stay under D:\\StoryStudio')
 dest.parent.mkdir(parents=True,exist_ok=True)
 start=time.monotonic()
 engine=Kokoro(str(ROOT/'models/kokoro/kokoro-v1.0.int8.onnx'),str(ROOT/'models/kokoro/voices-v1.0.bin'))
 pronunciation=engine.tokenizer.known(phonemize(text))
 samples,sr=engine.create(pronunciation,voice=args.voice,speed=args.speed,lang='en-us',is_phonemes=True)
 sf.write(str(dest),samples,sr,subtype='PCM_16')
 meta={'output':str(dest),'duration_seconds':len(samples)/sr,'sample_rate':sr,'voice':args.voice,'generation_seconds':round(time.monotonic()-start,2),'provider':'local Kokoro ONNX'}
 dest.with_suffix('.json').write_text(json.dumps(meta,indent=2))
 print(json.dumps(meta,indent=2))
if __name__=='__main__':main()

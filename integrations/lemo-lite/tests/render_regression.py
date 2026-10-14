"""Real-browser, actual MP4/audio/cancellation regressions; no mocked encoder."""
import argparse
from array import array
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import project
import renderer


def run(output,audio=None):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();checks=[];exports=[]
    doc=project.new_project();doc['scenes'][0].update(action='wave',duration=1,title='Hello, little star!')
    second=project.new_scene();second.update(character='rabbit',expression='curious',action='jump',background='sunset',duration=1,title='Let’s explore!')
    doc['scenes'].append(second)
    if audio:doc['audio']=str(Path(audio).resolve())
    project.save(doc,output/'regression-project.json')
    with renderer.scene_page(doc,640,360) as (page,errors):
        page.evaluate('window.render(.5)');first=page.screenshot()
        page.evaluate('window.render(1.5)');second=page.screenshot()
        assert page.evaluate('window.activeScene')==1
        page.evaluate('window.render(.5)');assert first==page.screenshot(),'Seeking changed the same frame'
        assert first!=second,'Scene changes have no effect'
        with Image.open(io.BytesIO(first)) as image:assert max(ImageStat.Stat(image).stddev)>20,'Blank frame'
        checks.extend(['deterministic seeking','scene transition','nonblank pixels'])
        variants=set()
        for kind in project.CHARACTERS:
            variant=copy.deepcopy(doc);variant['scenes'][0]['character']=kind
            page.evaluate('(doc)=>window.setProject(doc)',variant);page.evaluate('window.render(.5)')
            picture=page.screenshot();variants.add(hashlib.sha256(picture).hexdigest());(output/f'character-{kind}.png').write_bytes(picture)
        assert len(variants)==3,'Character rigs are not distinct'
        for field,values in [('expression',project.EXPRESSIONS),('action',project.ACTIONS)]:
            hashes=set()
            for value in values:
                variant=copy.deepcopy(doc);variant['scenes'][0][field]=value
                page.evaluate('(doc)=>window.setProject(doc)',variant);page.evaluate('window.render(.5)')
                hashes.add(hashlib.sha256(page.screenshot()).hexdigest())
            assert len(hashes)==len(values),f'{field} controls have no distinct effect'
        # Poses must interpolate smoothly, deterministically, and actually
        # move the character in the rendered canvas (not just update JSON).
        animated=copy.deepcopy(doc)
        animated['scenes'][0].update(action='idle',keyframes=[
            dict(t=0,x=.2,size=.7),dict(t=1,x=.7,size=1.2)])
        page.evaluate('(doc)=>window.setProject(doc)',animated)
        page.evaluate('window.render(.05)')
        before=page.evaluate('window.frameInfo')
        image_before=page.screenshot()
        page.evaluate('window.render(.95)')
        after=page.evaluate('window.frameInfo')
        image_after=page.screenshot()
        assert after['x']>before['x']+200,'Keyframe did not move character'
        assert after['scale']>before['scale']+.3,'Keyframe did not change character size'
        assert image_before!=image_after,'Position/size keyframes did not affect pixels'
        page.evaluate('window.render(.05)')
        assert image_before==page.screenshot(),'Keyframe seeking became nondeterministic'
        checks.append('reversible deterministic position and scale keyframes')
        # Portrait layout is deliberately re-composed, not stretched landscape.
        portrait=copy.deepcopy(doc);portrait['format']='Shorts / TikTok 9:16'
        page.set_viewport_size(dict(width=360,height=640));page.evaluate('(doc)=>window.setProject(doc)',portrait);page.evaluate('window.render(.5)')
        info=page.evaluate('window.frameInfo')
        assert info['portrait'] and 150<info['x']<550 and 700<info['y']<1000
        (output/'portrait-frame.png').write_bytes(page.screenshot())
        assert not errors,errors
        checks.extend(['three distinct reusable rigs','four expressions','six actions','portrait layout','no JS errors'])
    # Source rendering verifies both production presets, codecs, audio span and decode.
    for format_name in project.FORMATS:
        variant=copy.deepcopy(doc);variant['format']=format_name
        width,height,fps=project.dimensions(variant)
        target=output/('portrait-720p.mp4' if height>width else 'landscape-720p.mp4')
        args=argparse.Namespace(document=variant,output=str(target),duration=2,width=width,height=height,fps=fps,audio=None,overwrite=True)
        began=time.monotonic();renderer.export(args)
        details=renderer.verify(target,2,width,height,fps)
        decoded=subprocess.run([renderer.find_ffmpeg(),'-v','error','-i',str(target),'-vn','-f','s16le','-ac','1','-ar','24000','pipe:1'],capture_output=True,check=True,creationflags=renderer.NO_WINDOW)
        samples=array('h',decoded.stdout)
        assert len(samples)>=47000 and max(abs(x) for x in samples)>300,'Audio silent or truncated'
        decoded_video=subprocess.run([renderer.find_ffmpeg(),'-v','error','-i',str(target),'-vf','scale=64:64','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True,creationflags=renderer.NO_WINDOW)
        frames=[decoded_video.stdout[i:i+12288] for i in range(0,len(decoded_video.stdout),12288)]
        assert len(frames)==48 and len(set(frames))>20,'Frozen, missing or duplicate video frames'
        exports.append(dict(file=target.name,width=width,height=height,fps=fps,frames=48,seconds=round(time.monotonic()-began,2),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    checks.extend(['16:9 720p H.264/AAC','9:16 720p H.264/AAC','48 frames each','audible decoded samples','full decoding','animated decoded frames'])
    # Actual cancellation mid-stream must leave existing output unchanged.
    protected=output/'cancel-protected.mp4';protected.write_bytes(b'KEEP ORIGINAL')
    args=argparse.Namespace(document=doc,output=str(protected),duration=2,width=320,height=180,fps=12,audio=None,overwrite=True)
    event=threading.Event()
    try:
        renderer.export(args,lambda *_:event.set(),event)
        raise AssertionError('Cancellation did not stop rendering')
    except renderer.Cancelled:pass
    assert protected.read_bytes()==b'KEEP ORIGINAL';protected.unlink()
    assert not list(output.glob('*.partial.mp4'))
    checks.append('mid-render cancellation preserves existing file and removes staging')
    # A short soundtrack still produces audio throughout a two-second export.
    short=output/'short.wav';renderer.chime_wav(short,.5)
    args.audio=str(short);args.output=str(output/'short-audio-padded.mp4')
    renderer.export(args);renderer.verify(Path(args.output),2,320,180,12)
    checks.append('short imported soundtrack padded to story duration')
    report=dict(result='PASS',checks=checks,exports=exports,elapsed_seconds=round(time.monotonic()-start,2),audio_source='imported narration' if audio else 'original procedural chimes',platform=sys.platform)
    (output/'regression-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--audio')
    args=parser.parse_args();run(args.output,args.audio)

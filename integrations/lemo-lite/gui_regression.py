"""Exercise real Tk controls; called in source and inside the compiled EXE."""
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from PIL import ImageGrab
import project
from studio_ui import StudioApp


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gui-',dir=output) as td:
        app=StudioApp(workspace=td,auto_preview=False)
        callback_errors=[]
        app.report_callback_exception=lambda *args:callback_errors.append(str(args))
        def pump_until(check,timeout=60):
            deadline=time.monotonic()+timeout
            while not check():
                app.update()
                if callback_errors:raise AssertionError(callback_errors)
                if time.monotonic()>deadline:raise TimeoutError(app.status.get())
                time.sleep(.02)
            app.update()
        try:
            app.update()
            for width,height in [(1000,680),(1366,768)]:
                app.geometry(f'{width}x{height}');app.update()
                for widget in [app.export_button,app.save_button,app.timeline,app.scrubber,app.add_button,app.apply_button,app.tabs,app.stage]:
                    assert widget.winfo_ismapped(),str(widget)
                    assert widget.winfo_rooty()+widget.winfo_height()<=app.winfo_rooty()+app.winfo_height(),str(widget)
                    assert widget.winfo_rootx()+widget.winfo_width()<=app.winfo_rootx()+app.winfo_width(),str(widget)
            app.add_button.invoke();assert len(app.document['scenes'])==2
            app.duplicate_button.invoke();assert len(app.document['scenes'])==3
            app.delete_button.invoke();assert len(app.document['scenes'])==2
            app.fields['character'].set('rabbit');app.character_combo.event_generate('<<ComboboxSelected>>');app.update()
            app.fields['expression'].set('surprised');app.expression_combo.event_generate('<<ComboboxSelected>>');app.update()
            app.fields['action'].set('wave');app.action_combo.event_generate('<<ComboboxSelected>>');app.update()
            assert app.document['scenes'][1]['character']=='rabbit'
            assert app.document['scenes'][1]['expression']=='surprised'
            app.move_scene(-1);assert app.document['scenes'][0]['character']=='rabbit'
            app.tabs.select(2);app.update()
            app.format_var.set('Shorts / TikTok 9:16');app.format_combo.event_generate('<<ComboboxSelected>>');app.update()
            app.quality_var.set(list(project.QUALITIES)[1]);app.quality_combo.event_generate('<<ComboboxSelected>>');app.update()
            assert project.dimensions(app.document)==(360,640,12)
            app.tabs.select(0);app.update()
            path=Path(td)/'saved.json'
            with patch('studio_ui.filedialog.asksaveasfilename',return_value=str(path)):app.save_button.invoke()
            saved=project.load(path);assert saved==project.validate(app.document)
            app.document=project.new_project();app.refresh()
            with patch('studio_ui.filedialog.askopenfilename',return_value=str(path)):app.open_project()
            assert app.document==saved
            # Short real export driven through the UI dialog and asynchronous worker.
            app.document['scenes']=app.document['scenes'][:1];app.document['scenes'][0]['duration']=1
            app.refresh();app.time.set(.5);app.scrub()
            app.preview_enabled=True;app.preview_button.invoke()
            pump_until(lambda:not app.preview_busy)
            assert app.snapshot,app.status.get()
            app.update();ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height())).save(output/'editor-portrait.png')
            app.preview_enabled=False
            target=output/'gui-export.mp4'
            with patch('studio_ui.filedialog.asksaveasfilename',return_value=str(target)):app.export_button.invoke()
            assert app.busy and app.export_button.instate(['disabled'])
            pump_until(lambda:not app.busy,180)
            assert target.is_file() and 'Verified MP4 saved' in app.status.get(),app.status.get()
            assert app.export_button.instate(['!disabled'])
            assert not callback_errors,callback_errors
            (output/'gui-results.json').write_text(json.dumps(dict(result='PASS',checks=['laptop geometry','widget edits','scene order','portrait preset','save/open','browser frame','GUI MP4 export','worker completion'],compiled=bool(__import__('sys').frozen) if hasattr(__import__('sys'),'frozen') else False),indent=2))
        finally:
            app._close_server();app.destroy()

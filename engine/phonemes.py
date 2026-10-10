"""Single-process eSpeak adapter using its public API, without temporary DLL copies.

This helper is intentionally sequential: eSpeak uses process-global state.
"""
import ctypes,re
import espeakng_loader

def phonemize(text,language='en-us'):
 lib=ctypes.CDLL(espeakng_loader.get_library_path())
 lib.espeak_Initialize.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
 lib.espeak_Initialize.restype=ctypes.c_int
 lib.espeak_SetVoiceByName.argtypes=[ctypes.c_char_p]
 lib.espeak_SetVoiceByName.restype=ctypes.c_int
 lib.espeak_TextToPhonemes.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_int,ctypes.c_int]
 lib.espeak_TextToPhonemes.restype=ctypes.c_char_p
 if lib.espeak_Initialize(2,0,espeakng_loader.get_data_path().encode('utf8'),0)<=0:
  raise RuntimeError('Could not initialize the bundled eSpeak library')
 if lib.espeak_SetVoiceByName(language.encode())!=0:
  raise ValueError('Unsupported narration language')
 result=[]
 try:
  for match in re.finditer(r'([^.!?,;:\n]+)([.!?,;:]*)',text):
   phrase,punctuation=match.groups()
   buf=ctypes.create_string_buffer(phrase.strip().encode('utf8'))
   pointer=ctypes.cast(buf,ctypes.c_void_p)
   while pointer.value:
    old=pointer.value
    value=lib.espeak_TextToPhonemes(ctypes.byref(pointer),1,2)
    if value:result.append(value.decode('utf8'))
    if pointer.value==old:raise RuntimeError('Phonemizer did not advance')
   result.append(punctuation+' ')
  return ''.join(result).strip()
 finally:
  lib.espeak_Terminate()

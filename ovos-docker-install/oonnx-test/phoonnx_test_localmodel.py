import subprocess
import wave
from phoonnx.voice import SynthesisConfig, TTSVoice
import sounddevice as sd
import soundfile as sf
import logging


## https://github.com/TigreGotico/phoonnx/blob/dev/docs/quickstart.md
logger = logging.getLogger(__name__)
# Alternatively, for direct local file loading:
# from phoonnx.voice import TTSVoice

class OonnxTest:
    def __init__(self):
        logger.info('Phoonnx initialized.')

    def synthesize_text_to_wav(self):

        logger.info('Phoonnx synthesize_text_to_wav.')
        # OpenVoiceOS/pipertts_de-DE_miro
        # Adjust the voice key depending on your index cache or local setup
        voice = TTSVoice.load("model.onnx", "model.onnx.json")
    
        cfg = SynthesisConfig(
            length_scale=1.1,   # >1 slower, <1 faster
            noise_scale=0.667,  # generator noise / variation
            volume=2.0,
        )

        with wave.open("out.wav", "wb") as wav_file:
            voice.synthesize_wav("Hallo, mein Name ist Albrecht.", wav_file, cfg)

    def play_audio(self, file_path="out.wav"):
        logger.info('Phoonnx play_audio')
        data, fs = sf.read(file_path)
        sd.play(data, fs)
        sd.wait()

    #def play_audio_aplay(self, file_path="out.wav"):
        # Calls the native ALSA player
       # subprocess.run(["aplay", file_path], check=True)

# ===========================================================
# Main
# ===========================================================
if __name__ == "__main__":
    test = OonnxTest()
    try:
        logger.info('Started')
        test.synthesize_text_to_wav()
        logger.info('Audio synthesis complete. Playing audio...')
        test.play_audio()
        logger.info('Audio playing complete.')
    except Exception as e:
        logger.info('error occurred during the test.')
        logger.exception(e)
    finally:
        logger.info('Test completed. Check \'out.wav\' for the synthesized audio.')
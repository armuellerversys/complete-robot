import subprocess
import wave
from phoonnx.model_manager import TTSModelManager
import sounddevice as sd
import soundfile as sf
import logging

logger = logging.getLogger(__name__)
# Alternatively, for direct local file loading:
# from phoonnx.voice import TTSVoice

class OonnxTest:
    def __init__(self):
        logger.info('Phoonnx __init__.')
        self.manager = TTSModelManager()
        self.manager.load()
        self.manager.merge_default_voices()
        logger.info('Phoonnx initialized.')

    def synthesize_text_to_wav(self):
        logger.info('Phoonnx start synthesize_text_to_wav')
        # Adjust the voice key depending on your index cache or local setup
        # https://huggingface.co/OpenVoiceOS/phoonnx-coqui-vits -> coqui/de-thorsten-vits
        voice = self.manager.voices["OpenVoiceOS/phoonnx-coqui-vits"].load()
        with wave.open("out.wav", "wb") as wav_file:
            voice.synthesize_wav("Hallo, mein Name ist Albrecht.", wav_file)
        logger.info('Phoonnx end synthesize_text_to_wav')

    def play_audio(self, file_path="out.wav"):
        logger.info('Phoonnx start splay_audio')
        data, fs = sf.read(file_path)
        sd.play(data, fs)
        sd.wait()
        logger.info('Phoonnx end splay_audio')

    #def play_audio_aplay(self, file_path="out.wav"):
        # Calls the native ALSA player
       # subprocess.run(["aplay", file_path], check=True)

# ===========================================================
# Main
# ===========================================================
if __name__ == "__main__":
    test = OonnxTest()
    try:
        logger.info('Start OonnxTest')
        test.synthesize_text_to_wav()
        logger.info('Audio synthesis complete. Playing audio...')
        test.play_audio()
        logger.info('Audio playing complete.')
    except Exception as e:
        logger.info('error occurred during the test.')
        logger.exception(e)
    finally:
        logger.info('Test completed. Check \'out.wav\' for the synthesized audio.')
import sys
import io
import wave
from phoonnx.voice import SynthesisConfig, TTSVoice
import sounddevice as sd
import soundfile as sf
import logging
from flask import Flask, Response, request

app = Flask(__name__)

## https://github.com/TigreGotico/phoonnx/blob/dev/docs/quickstart.md
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)
# Alternatively, for direct local file loading:
# from phoonnx.voice import TTSVoice
# http://192.168.4.6:7000/say?text=hallo


@app.route("/say", methods=["GET"])
def say_text():
    text = request.args.get("text", "").strip()

    if not text:
        return Response("Missing text parameter", status=400)

    tts.synthesize_and_play(text)
    return Response("Playback complete", status=200)

class OonnxTest:
    def __init__(self):
        logger.info("Phoonnx initialized.")

        # Load the model once, rather than for every request
        self.voice = TTSVoice.load("model.onnx", "model.onnx.json")

        self.cfg = SynthesisConfig(
            length_scale=1.2,
            noise_scale=0.667,
            volume=2.0,
        )

    def synthesize_and_play(self, text):
        try:
            logger.info("Synthesizing: %s", text)

            # Create WAV data in memory, not on disk
            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, "wb") as wav_file:
                    self.voice.synthesize_wav(
                        text, wav_file, self.cfg
                    )

                wav_buffer.seek(0)
                data, sample_rate = sf.read(wav_buffer, dtype="float32")

            logger.info("Playing synthesized audio")
            sd.play(data, sample_rate)
            sd.wait()

            logger.info("Playback complete")
        except Exception as e:
                logger.info('error occurred during synthesize_and_play.')
                logger.exception(e)


tts = OonnxTest()

# ===========================================================
# Main
# ===========================================================
if __name__ == "__main__":
   
    try:
        logger.info('Started')
        app.run(host='0.0.0.0', port=5500, use_reloader=False)

        tts.synthesize_and_play("Hallo, mein Name ist Albrecht.")

        logger.info('Audio playing complete.')
    except Exception as e:
        logger.info('error occurred during the test.')
        logger.exception(e)
    finally:
        logger.info('Test completed. Check \'out.wav\' for the synthesized audio.')
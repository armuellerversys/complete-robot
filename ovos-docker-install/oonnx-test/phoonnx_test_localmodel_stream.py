import sys
import io
import wave
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import logging
from flask import Flask, Response, request
from phoonnx.voice import SynthesisConfig, TTSVoice

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

class OonnxService:
    def __init__(self):
        logger.info("Phoonnx initialized.")
        # Load the model once
        self.voice = TTSVoice.load("model.onnx", "model.onnx.json")
        self.cfg = SynthesisConfig(
            length_scale=1.2,
            noise_scale=0.667,
            volume=2.0,
        )

    def synthesize_to_bytes(self, text, target_sample_rate=None):
        logger.info("Synthesizing text: %s", text)

        # Generate raw WAV from the ONNX model into an in-memory buffer
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file, self.cfg)
            
            wav_buffer.seek(0)
            data, model_sample_rate = sf.read(wav_buffer, dtype="float32")

        sample_rate = model_sample_rate

        logger.info("Generated audio sample rate: %s Hz", model_sample_rate)

        # Optional: Resample if a specific target sample rate is needed for the client
        if target_sample_rate and model_sample_rate != target_sample_rate:
            logger.info("Resampling audio from %s Hz to %s Hz", model_sample_rate, target_sample_rate)
            gcd = np.gcd(target_sample_rate, int(model_sample_rate))
            up = target_sample_rate // gcd
            down = int(model_sample_rate) // gcd
            data = resample_poly(data, up, down)
            sample_rate = target_sample_rate

        # Export processed audio data back to an in-memory WAV stream (16-bit PCM)
        out_buffer = io.BytesIO()
        sf.write(out_buffer, data, sample_rate, format='WAV', subtype='PCM_16')
        out_buffer.seek(0)
        return out_buffer.read()

# Initialize TTS service instance
tts = OonnxService()

@app.route("/say", methods=["GET"])
def say_text():
    text = request.args.get("text", "").strip()

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        # You can pass an optional target_sample_rate=16000 if your client requires it,
        # otherwise leaving it out streams at the model's native sample rate (22050 Hz).
        audio_bytes = tts.synthesize_to_bytes(text)
        
        # Return the audio stream with the correct mimetype for browsers/clients
        return Response(audio_bytes, mimetype="audio/wav")

    except Exception:
        logger.exception("TTS synthesis failed")
        return Response("TTS synthesis failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Flask TTS server on port 5500...")
    app.run(host="0.0.0.0", port=5600, use_reloader=False)
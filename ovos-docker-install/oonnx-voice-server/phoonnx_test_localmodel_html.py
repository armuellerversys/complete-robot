import sys
import io
import wave
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import logging
from flask import Flask, Response, request, render_template_string
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

        logger.info("Generated audio sample rate: %s Hz", model_sample_rate)

        sample_rate = model_sample_rate

        # Optional: Resample if a specific target sample rate is needed
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

# HTML Frontend Template served at the root URL
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoonnx TTS Web Player</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 40px; display: flex; justify-content: center; }
        .card { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 500px; }
        h2 { margin-top: 0; color: #007bff; }
        textarea { width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; box-sizing: border-box; resize: vertical; }
        button { background-color: #007bff; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; margin-top: 15px; width: 100%; }
        button:hover { background-color: #0056b3; }
        audio { width: 100%; margin-top: 20px; }
        .loading { font-style: italic; color: #666; margin-top: 10px; display: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Phoonnx TTS Player</h2>
        <p>Type text below to synthesize and listen instantly:</p>
        <textarea id="textInput">Hallo, mein Name ist Albrecht.</textarea>
        <button onclick="synthesizeAndPlay()">Synthesize & Play</button>
        <div id="loadingStatus" class="loading">Synthesizing audio...</div>
        <audio id="audioPlayer" controls></audio>
    </div>

    <script>
        function synthesizeAndPlay() {
            const text = document.getElementById('textInput').value;
            const audioPlayer = document.getElementById('audioPlayer');
            const loadingStatus = document.getElementById('loadingStatus');

            if (!text.trim()) {
                alert("Please enter some text.");
                return;
            }

            loadingStatus.style.display = 'block';
            
            // Fetch audio stream from the /say endpoint with a timestamp to prevent caching
            const audioUrl = `/say?text=${encodeURIComponent(text)}&t=${Date.now()}`;
            
            audioPlayer.src = audioUrl;
            audioPlayer.load();
            
            audioPlayer.oncanplaythrough = function() {
                loadingStatus.style.display = 'none';
                audioPlayer.play();
            };
            
            audioPlayer.onerror = function() {
                loadingStatus.style.display = 'none';
                alert("Error playing audio stream.");
            };
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/say", methods=["GET"])
def say_text():
    text = request.args.get("text", "").strip()

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        audio_bytes = tts.synthesize_to_bytes(text)
        return Response(audio_bytes, mimetype="audio/wav")

    except Exception:
        logger.exception("TTS synthesis failed")
        return Response("TTS synthesis failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Flask TTS server on port 5500...")
    app.run(host="0.0.0.0", port=5700, use_reloader=False)
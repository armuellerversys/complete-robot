import sys
import io
import os
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import logging
from flask import Flask, Response, request, render_template_string, jsonify
from kokoro_onnx import Kokoro
from german_normalizer import normalize_german_text

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

class KokoroService:
    def __init__(self):
        logger.info("Initializing Kokoro-82M ONNX TTS Service...")
        
        model_path = "/home/ovos/model/kokoro-martin.onnx"
        voices_path = "/home/ovos/model/voices-martin.npz"
        
        try:
            logger.info("Loading Kokoro model from %s...", model_path)
            self.kokoro = Kokoro(model_path, voices_path)
            logger.info("Kokoro model successfully loaded. Available voices: %s", self.kokoro.get_voices())
        except Exception as e:
            logger.error("FAILED to load Kokoro model: %s", e)
            self.kokoro = None

    def get_available_speakers(self):
        if not self.kokoro:
            return []
        voices = self.kokoro.get_voices()
        return [{"id": v, "name": f"Kokoro - {v.capitalize()} (German HQ)", "length_scale": 1.0, "volume": 2.0} for v in voices]

    def synthesize_to_bytes(self, text, speaker_id="martin", length_scale=1.0, volume=2.0, target_sample_rate=None):
        if not self.kokoro:
            raise RuntimeError("Kokoro model is not loaded.")

        # Apply German Text Normalization
        normalized_text = normalize_german_text(text)
        logger.info("Raw input text: %s", text)
        logger.info("Normalized text: %s", normalized_text)

        speed = max(0.5, min(2.0, 1.0 / float(length_scale)))

        # Generate audio samples using the normalized string
        samples, sample_rate = self.kokoro.create(normalized_text, voice=speaker_id, speed=speed, lang="de")
        
        data = np.asarray(samples, dtype=np.float32)
        
        vol = float(volume)
        if vol != 1.0:
            data = data * (vol / 2.0)

        if target_sample_rate and sample_rate != target_sample_rate:
            gcd = np.gcd(target_sample_rate, int(sample_rate))
            up = target_sample_rate // gcd
            down = int(sample_rate) // gcd
            data = resample_poly(data, up, down)
            sample_rate = target_sample_rate

        out_buffer = io.BytesIO()
        sf.write(out_buffer, data, sample_rate, format='WAV', subtype='PCM_16')
        out_buffer.seek(0)
        return out_buffer.read()

tts_service = KokoroService()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kokoro German TTS Player with Preview</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 40px; display: flex; justify-content: center; }
        .card { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 550px; }
        h2 { margin-top: 0; color: #007bff; }
        label { display: block; margin-top: 15px; margin-bottom: 5px; font-weight: bold; }
        select, textarea, input[type="range"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; box-sizing: border-box; }
        textarea { height: 90px; resize: vertical; }
        .preview-box { background: #e9ecef; padding: 10px; border-radius: 4px; font-size: 14px; margin-top: 5px; color: #495057; display: none; }
        .checkbox-group { display: flex; align-items: center; margin-top: 15px; }
        .checkbox-group input { width: auto; margin-right: 10px; }
        .slider-group { display: flex; justify-content: space-between; align-items: center; margin-top: 5px; }
        .slider-group input { flex-grow: 1; margin-right: 15px; }
        .slider-value { font-weight: bold; min-width: 40px; text-align: right; }
        button { background-color: #007bff; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; margin-top: 25px; width: 100%; }
        button:hover { background-color: #0056b3; }
        audio { width: 100%; margin-top: 20px; }
        .loading { font-style: italic; color: #666; margin-top: 10px; display: none; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Kokoro German TTS Player</h2>
        
        <label for="speakerSelect">Select Voice:</label>
        <select id="speakerSelect"></select>

        <label for="textInput">Text to Synthesize:</label>
        <textarea id="textInput" oninput="liveUpdatePreview()">Der Termin ist um 18:30 Uhr bei Dr. Meier. Kostenpunkt ca. 3,50 €.</textarea>
        
        <div class="checkbox-group">
            <input type="checkbox" id="showPreview" onchange="togglePreview()">
            <label for="showPreview" style="margin-top:0; font-weight:normal;">Preview Normalization (Spoken text)</label>
        </div>
        <div id="previewContainer" class="preview-box"><strong>Normalized:</strong> <span id="previewText">...</span></div>

        <label style="margin-top: 20px;">Speed Scale: <span style="font-weight:normal; font-size:0.9em;">(Lower = faster, Higher = slower)</span></label>
        <div class="slider-group">
            <input type="range" id="lengthScale" min="0.5" max="2.0" step="0.05" value="1.0" oninput="updateVal('lengthScale', 'lengthVal')">
            <span id="lengthVal" class="slider-value">1.0</span>
        </div>

        <label>Volume:</label>
        <div class="slider-group">
            <input type="range" id="volume" min="0.5" max="5.0" step="0.1" value="2.0" oninput="updateVal('volume', 'volVal')">
            <span id="volVal" class="slider-value">2.0</span>
        </div>

        <button onclick="synthesizeAndPlay()">Synthesize & Play</button>
        <div id="loadingStatus" class="loading">Synthesizing audio...</div>
        <audio id="audioPlayer" controls></audio>
    </div>

    <script>
        window.onload = async function() {
            try {
                const response = await fetch('/speakers');
                const speakers = await response.json();
                const select = document.getElementById('speakerSelect');
                select.innerHTML = '';
                speakers.forEach(spk => {
                    const option = document.createElement('option');
                    option.value = spk.id;
                    option.textContent = spk.name;
                    select.appendChild(option);
                });
            } catch (err) {
                console.error("Failed to load voices list", err);
            }
        };

        function updateVal(sliderId, spanId) {
            document.getElementById(spanId).textContent = document.getElementById(sliderId).value;
        }

        async function togglePreview() {
            const container = document.getElementById('previewContainer');
            const checkbox = document.getElementById('showPreview');
            if (checkbox.checked) {
                container.style.display = 'block';
                await fetchPreviewText();
            } else {
                container.style.display = 'none';
            }
        }

        async function liveUpdatePreview() {
            const checkbox = document.getElementById('showPreview');
            if (checkbox.checked) {
                await fetchPreviewText();
            }
        }

        async function fetchPreviewText() {
            const text = document.getElementById('textInput').value;
            try {
                const response = await fetch(`/normalize?text=${encodeURIComponent(text)}`);
                const data = await response.json();
                document.getElementById('previewText').textContent = data.normalized;
            } catch (err) {
                document.getElementById('previewText').textContent = "Error fetching preview.";
            }
        }

        function synthesizeAndPlay() {
            const text = document.getElementById('textInput').value;
            const speakerId = document.getElementById('speakerSelect').value;
            const lengthScale = document.getElementById('lengthScale').value;
            const volume = document.getElementById('volume').value;
            
            const audioPlayer = document.getElementById('audioPlayer');
            const loadingStatus = document.getElementById('loadingStatus');

            if (!text.trim()) {
                alert("Please enter some text.");
                return;
            }

            loadingStatus.style.display = 'block';
            
            const params = new URLSearchParams({
                text: text,
                speaker: speakerId,
                length_scale: lengthScale,
                volume: volume,
                t: Date.now()
            });

            audioPlayer.src = `/say?${params.toString()}`;
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

@app.route("/speakers", methods=["GET"])
def get_speakers():
    return jsonify(tts_service.get_available_speakers())

@app.route("/normalize", methods=["GET"])
def normalize_endpoint():
    text = request.args.get("text", "").strip()
    normalized = normalize_german_text(text)
    return jsonify({"original": text, "normalized": normalized})

@app.route("/say", methods=["GET"])
def say_text():
    text = request.args.get("text", "").strip()
    speaker_id = request.args.get("speaker", "martin")
    length_scale = request.args.get("length_scale", 1.0)
    volume = request.args.get("volume", 2.0)

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        audio_bytes = tts_service.synthesize_to_bytes(
            text, 
            speaker_id=speaker_id, 
            length_scale=length_scale, 
            volume=volume
        )
        return Response(audio_bytes, mimetype="audio/wav")

    except Exception:
        logger.exception("TTS synthesis failed")
        return Response("TTS synthesis failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Kokoro ONNX Flask TTS server with Normalization on port 5500...")
    app.run(host="0.0.0.0", port=5500, use_reloader=False)
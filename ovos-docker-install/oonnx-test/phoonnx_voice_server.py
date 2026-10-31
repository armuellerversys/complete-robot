import sys
import io
import os
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import sounddevice as sd
import logging
from flask import Flask, Response, request, render_template_string, jsonify
from kokoro_onnx import Kokoro
from german_normalizer import normalize_german_text


##
## curl "http://192.168.4.6:5500/speak_local?text=Hallo%20Albrecht,%20Bewegung%20im%20Garten%20erkannt&volume=3.0"
## curl -X POST "http://<YOUR_PI_IP>:5500/speak_local" \
##     -H "Content-Type: application/json" \
##     -d '{"text": "Die Temperatur im Wohnzimmer beträgt 21 Grad.", "volume": 2.5}'


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

class KokoroLocalServerService:
    def __init__(self):
        logger.info("Initializing Kokoro-82M TTS Server & Local Player...")
        
        model_path = "/home/ovos/model/kokoro-martin.onnx"
        voices_path = "/home/ovos/model/voices-martin.npz"
        
        try:
            self.kokoro = Kokoro(model_path, voices_path)
            logger.info("Kokoro model successfully loaded.")
        except Exception as e:
            logger.error("FAILED to load Kokoro model: %s", e)
            self.kokoro = None

    def get_available_speakers(self):
        if not self.kokoro:
            return []
        voices = self.kokoro.get_voices()
        return [{"id": v, "name": f"Kokoro - {v.capitalize()} (German HQ)", "length_scale": 1.0, "volume": 2.0} for v in voices]

    def synthesize_raw_audio(self, text, speaker_id="martin", length_scale=1.0, volume=2.0, target_sample_rate=None):
        if not self.kokoro:
            raise RuntimeError("Kokoro model is not loaded.")

        # Apply German Text Normalization
        normalized_text = normalize_german_text(text)
        logger.info("Normalized text: %s", normalized_text)

        speed = max(0.5, min(2.0, 1.0 / float(length_scale)))

        # Generate audio samples
        samples, sample_rate = self.kokoro.create(normalized_text, voice=speaker_id, speed=speed, lang="de")
        data = np.asarray(samples, dtype=np.float32)
        
        # Apply software volume scaling
        vol = float(volume)
        if vol != 1.0:
            data = data * (vol / 2.0)

        # Optional resampling for hardware/streaming compliance
        if target_sample_rate and sample_rate != target_sample_rate:
            gcd = np.gcd(target_sample_rate, int(sample_rate))
            up = target_sample_rate // gcd
            down = int(sample_rate) // gcd
            data = resample_poly(data, up, down)
            sample_rate = target_sample_rate

        return data, sample_rate

    def synthesize_to_wav_bytes(self, text, speaker_id="martin", length_scale=1.0, volume=2.0, target_sample_rate=None):
        data, sample_rate = self.synthesize_raw_audio(text, speaker_id, length_scale, volume, target_sample_rate)
        
        out_buffer = io.BytesIO()
        sf.write(out_buffer, data, sample_rate, format='WAV', subtype='PCM_16')
        out_buffer.seek(0)
        return out_buffer.read()

    def play_locally(self, text, speaker_id="martin", length_scale=1.0, volume=2.0, output_device=0):
        """Synthesizes text and plays it through the local attached sounddevice output."""
        # Kokoro native sample rate is 24000 Hz. Resample to 16000 Hz or device default if needed, 
        # or let sounddevice match it if supported. Let's target 16000 Hz for Seeed HAT compatibility.
        target_sr = 16000 
        data, sample_rate = self.synthesize_raw_audio(text, speaker_id, length_scale, volume, target_sample_rate=target_sr)

        logger.info("Playing locally on device %s at %d Hz...", output_device, target_sr)
        sd.play(data, target_sr, device=output_device)
        sd.wait()
        logger.info("Local playback complete.")

tts_service = KokoroLocalServerService()

# HTML Frontend Template with Local Play & Stream Options
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kokoro TTS Voice Server</title>
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
        .btn-row { display: flex; gap: 10px; margin-top: 25px; }
        button { background-color: #007bff; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; flex: 1; }
        button.secondary { background-color: #28a745; }
        button:hover { opacity: 0.9; }
        audio { width: 100%; margin-top: 20px; }
        .loading { font-style: italic; color: #666; margin-top: 10px; display: none; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Kokoro TTS Voice Server</h2>
        
        <label for="speakerSelect">Select Voice:</label>
        <select id="speakerSelect"></select>

        <label for="textInput">Text to Speak:</label>
        <textarea id="textInput" oninput="liveUpdatePreview()">Hallo Albrecht, das System ist betriebsbereit.</textarea>
        
        <div class="checkbox-group">
            <input type="checkbox" id="showPreview" onchange="togglePreview()">
            <label for="showPreview" style="margin-top:0; font-weight:normal;">Preview Spoken Normalization</label>
        </div>
        <div id="previewContainer" class="preview-box"><strong>Normalized:</strong> <span id="previewText">...</span></div>

        <label style="margin-top: 20px;">Speed Scale:</label>
        <div class="slider-group">
            <input type="range" id="lengthScale" min="0.5" max="2.0" step="0.05" value="1.0" oninput="updateVal('lengthScale', 'lengthVal')">
            <span id="lengthVal" class="slider-value">1.0</span>
        </div>

        <label>Volume:</label>
        <div class="slider-group">
            <input type="range" id="volume" min="0.5" max="5.0" step="0.1" value="2.0" oninput="updateVal('volume', 'volVal')">
            <span id="volVal" class="slider-value">2.0</span>
        </div>

        <div class="btn-row">
            <button onclick="playLocally()" class="secondary">Play Locally (Pi Speaker)</button>
            <button onclick="synthesizeAndStream()">Stream in Browser</button>
        </div>
        
        <div id="loadingStatus" class="loading">Processing speech...</div>
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
            if (document.getElementById('showPreview').checked) {
                container.style.display = 'block';
                await fetchPreviewText();
            } else {
                container.style.display = 'none';
            }
        }

        async function liveUpdatePreview() {
            if (document.getElementById('showPreview').checked) {
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

        async function playLocally() {
            const text = document.getElementById('textInput').value;
            const speakerId = document.getElementById('speakerSelect').value;
            const lengthScale = document.getElementById('lengthScale').value;
            const volume = document.getElementById('volume').value;

            if (!text.trim()) { alert("Please enter text."); return; }

            const params = new URLSearchParams({ text, speaker: speakerId, length_scale: lengthScale, volume });
            try {
                const res = await fetch(`/speak_local?${params.toString()}`);
                const msg = await res.text();
                alert(msg);
            } catch (e) {
                alert("Error triggering local playback.");
            }
        }

        function synthesizeAndStream() {
            const text = document.getElementById('textInput').value;
            const speakerId = document.getElementById('speakerSelect').value;
            const lengthScale = document.getElementById('lengthScale').value;
            const volume = document.getElementById('volume').value;
            
            const audioPlayer = document.getElementById('audioPlayer');
            const loadingStatus = document.getElementById('loadingStatus');

            if (!text.trim()) { alert("Please enter text."); return; }

            loadingStatus.style.display = 'block';
            
            const params = new URLSearchParams({ text, speaker: speakerId, length_scale: lengthScale, volume, t: Date.now() });
            audioPlayer.src = `/say?${params.toString()}`;
            audioPlayer.load();
            
            audioPlayer.oncanplaythrough = function() {
                loadingStatus.style.display = 'none';
                audioPlayer.play();
            };
            audioPlayer.onerror = function() {
                loadingStatus.style.display = 'none';
                alert("Error streaming audio.");
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
    return jsonify({"original": text, "normalized": normalize_german_text(text)})

@app.route("/say", methods=["GET"])
def say_text():
    """HTTP endpoint to stream WAV audio bytes."""
    text = request.args.get("text", "").strip()
    speaker_id = request.args.get("speaker", "martin")
    length_scale = request.args.get("length_scale", 1.0)
    volume = request.args.get("volume", 2.0)

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        audio_bytes = tts_service.synthesize_to_wav_bytes(text, speaker_id, length_scale, volume)
        return Response(audio_bytes, mimetype="audio/wav")
    except Exception:
        logger.exception("TTS streaming failed")
        return Response("TTS streaming failed", status=500)

@app.route("/speak_local", methods=["GET", "POST"])
def speak_local():
    """HTTP endpoint to trigger playback directly on the Pi's attached speaker device."""
    # Supports both GET query params and JSON POST bodies for easy integration with home automation
    if request.method == "POST":
        data = request.get_json() or {}
        text = data.get("text", "").strip()
        speaker_id = data.get("speaker", "martin")
        length_scale = data.get("length_scale", 1.0)
        volume = data.get("volume", 2.0)
    else:
        text = request.args.get("text", "").strip()
        speaker_id = request.args.get("speaker", "martin")
        length_scale = request.args.get("length_scale", 1.0)
        volume = request.args.get("volume", 2.0)

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        tts_service.play_locally(text, speaker_id, length_scale, volume)
        return Response("Local playback completed successfully", status=200)
    except Exception:
        logger.exception("Local speaker playback failed")
        return Response("Local speaker playback failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Kokoro TTS Voice Server on port 5500...")
    app.run(host="0.0.0.0", port=5500, use_reloader=False)
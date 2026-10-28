import sys
import io
import wave
import json
import os
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import logging
from flask import Flask, Response, request, render_template_string, jsonify
from phoonnx.voice import SynthesisConfig, TTSVoice

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

class MultiSpeakerOonnxService:
    def __init__(self, config_file="/home/ovos/model/voices_config.json"):
        logger.info("Initializing Multi-Speaker Phoonnx Service...")
        self.voices_config = self._load_config(config_file)
        
        self.loaded_voices = {}
        for key, conf in self.voices_config.items():
            try:
                logger.info("Loading voice '%s' from %s", conf["name"], conf["model_path"])
                self.loaded_voices[key] = TTSVoice.load(conf["model_path"], conf["config_path"])
                logger.info("Successfully loaded: %s", key)
            except Exception as e:
                logger.error("FAILED to load voice %s from %s. Error: %s", key, conf["model_path"], e)

        if (len(self.loaded_voices ) == 0):
            logger.error("FAILED to load voices from configuration file")

    def _load_config(self, config_file):
        if not os.path.exists(config_file):
            logger.warning("Config file '%s' not found!", config_file)
            return {}
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error reading config file: %s", e)
            return {}

    def get_available_speakers(self):
        result = []
        for k, v in self.voices_config.items():
            if k in self.loaded_voices:
                result.append({
                    "id": k, 
                    "name": v["name"],
                    "length_scale": v.get("length_scale", 1.0),
                    "noise_scale": v.get("noise_scale", 0.667),
                    "volume": v.get("volume", 2.0)
                })
        return result

    def synthesize_to_bytes(self, text, speaker_id=None, length_scale=1.0, noise_scale=0.667, volume=2.0, target_sample_rate=None):
        if not speaker_id or speaker_id not in self.loaded_voices:
            available = list(self.loaded_voices.keys())
            if not available:
                raise ValueError("No voices are currently loaded.")
            speaker_id = available[0]

        voice = self.loaded_voices[speaker_id]
        
        # Build configuration using dynamic parameters passed from frontend
        cfg = SynthesisConfig(
            length_scale=float(length_scale),
            noise_scale=float(noise_scale),
            volume=float(volume),
        )

        logger.info("Synthesizing with '%s' (speed=%.2f, noise=%.2f, vol=%.2f): %s", 
                    speaker_id, cfg.length_scale, cfg.noise_scale, cfg.volume, text)

        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file, cfg)
            
            wav_buffer.seek(0)
            data, model_sample_rate = sf.read(wav_buffer, dtype="float32")

        sample_rate = model_sample_rate
        if target_sample_rate and model_sample_rate != target_sample_rate:
            gcd = np.gcd(target_sample_rate, int(model_sample_rate))
            up = target_sample_rate // gcd
            down = int(model_sample_rate) // gcd
            data = resample_poly(data, up, down)
            sample_rate = target_sample_rate

        out_buffer = io.BytesIO()
        sf.write(out_buffer, data, sample_rate, format='WAV', subtype='PCM_16')
        out_buffer.seek(0)
        return out_buffer.read()

tts_service = MultiSpeakerOonnxService("voices_config.json")

# HTML Frontend Template with Parameter Sliders
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configurable Multi-Speaker TTS Player</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 40px; display: flex; justify-content: center; }
        .card { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 550px; }
        h2 { margin-top: 0; color: #007bff; }
        label { display: block; margin-top: 15px; margin-bottom: 5px; font-weight: bold; }
        select, textarea, input[type="range"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; box-sizing: border-box; }
        textarea { height: 90px; resize: vertical; }
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
        <h2>Configurable TTS Player</h2>
        
        <label for="speakerSelect">Select Speaker / Voice:</label>
        <select id="speakerSelect" onchange="onSpeakerChange()">
            <!-- Populated via JS -->
        </select>

        <label for="textInput">Text to Synthesize:</label>
        <textarea id="textInput">Hallo, mein Name ist Albrecht. Wie kann ich Ihnen heute helfen?</textarea>
        
        <label>Speed (Length Scale): <span style="font-weight:normal; font-size:0.9em;">(Lower = faster, Higher = slower)</span></label>
        <div class="slider-group">
            <input type="range" id="lengthScale" min="0.5" max="2.0" step="0.05" value="1.0" oninput="updateVal('lengthScale', 'lengthVal')">
            <span id="lengthVal" class="slider-value">1.0</span>
        </div>

        <label>Expressiveness (Noise Scale): <span style="font-weight:normal; font-size:0.9em;">(Variation/Emotion)</span></label>
        <div class="slider-group">
            <input type="range" id="noiseScale" min="0.1" max="1.5" step="0.05" value="0.67" oninput="updateVal('noiseScale', 'noiseVal')">
            <span id="noiseVal" class="slider-value">0.67</span>
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
        let speakersData = [];

        window.onload = async function() {
            try {
                const response = await fetch('/speakers');
                speakersData = await response.json();
                const select = document.getElementById('speakerSelect');
                select.innerHTML = '';
                speakersData.forEach(spk => {
                    const option = document.createElement('option');
                    option.value = spk.id;
                    option.textContent = spk.name;
                    select.appendChild(option);
                });
                if (speakersData.length > 0) {
                    select.selectedIndex = 0;
                    onSpeakerChange();
                }
            } catch (err) {
                console.error("Failed to load speakers list", err);
            }
        };

        function onSpeakerChange() {
            const selectedId = document.getElementById('speakerSelect').value;
            const spk = speakersData.find(s => s.id === selectedId);
            if (spk) {
                document.getElementById('lengthScale').value = spk.length_scale;
                document.getElementById('lengthVal').textContent = spk.length_scale;

                document.getElementById('noiseScale').value = spk.noise_scale;
                document.getElementById('noiseVal').textContent = spk.noise_scale;

                document.getElementById('volume').value = spk.volume;
                document.getElementById('volVal').textContent = spk.volume;
            }
        }

        function updateVal(sliderId, spanId) {
            document.getElementById(spanId).textContent = document.getElementById(sliderId).value;
        }

        function synthesizeAndPlay() {
            const text = document.getElementById('textInput').value;
            const speakerId = document.getElementById('speakerSelect').value;
            const lengthScale = document.getElementById('lengthScale').value;
            const noiseScale = document.getElementById('noiseScale').value;
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
                noise_scale: noiseScale,
                volume: volume,
                t: Date.now()
            });

            const audioUrl = `/say?${params.toString()}`;
            
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

@app.route("/speakers", methods=["GET"])
def get_speakers():
    return jsonify(tts_service.get_available_speakers())

@app.route("/say", methods=["GET"])
def say_text():
    text = request.args.get("text", "").strip()
    speaker_id = request.args.get("speaker")
    length_scale = request.args.get("length_scale", 1.0)
    noise_scale = request.args.get("noise_scale", 0.667)
    volume = request.args.get("volume", 2.0)

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        audio_bytes = tts_service.synthesize_to_bytes(
            text, 
            speaker_id=speaker_id, 
            length_scale=length_scale, 
            noise_scale=noise_scale, 
            volume=volume
        )
        return Response(audio_bytes, mimetype="audio/wav")

    except Exception:
        logger.exception("TTS synthesis failed")
        return Response("TTS synthesis failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Configurable Multi-Speaker Flask TTS server on port 5700...")
    app.run(host="0.0.0.0", port=5700, use_reloader=False)
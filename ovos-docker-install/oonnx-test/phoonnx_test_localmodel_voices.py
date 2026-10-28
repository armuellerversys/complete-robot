import sys
import io
import os
import wave
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

# Define the exact same paths you are using in your Flask app
voices_config = {
    "speaker_albrecht": {
        "name": "Albrecht (miro_de-DE- Default)",
        "model_path": "/home/ovos/model/miro_de-DE.onnx",
        "config_path": "/home/ovos/model/miro_de-DE.onnx.json"
    },
    "speaker_thorsten": {
        "name": "thorsten Voice (German)",
        "model_path": "/home/ovos/model/phoonnx-de-thorsten-model.onnx",
        "config_path": "/home/ovos/model/phoonnx-de-thorsten-model.onnx.json"
    },
    "speaker_thorsten-medium": {
        "name": "thorsten-medium (German)",
        "model_path": "/home/ovos/model/de_DE-thorsten-medium.onnx",
        "config_path": "/home/ovos/model/de_DE-thorsten-medium.onnx.json"
    }
}

def test_load_models():
    logger.info("Starting model file and loading checks...")
    
    for key, conf in voices_config.items():
        logger.info("-" * 40)
        logger.info("Checking Voice ID: '%s' (%s)", key, conf["name"])
        
        model_path = conf["model_path"]
        config_path = conf["config_path"]
        
        # 1. Check if ONNX model file exists
        if os.path.exists(model_path):
            file_size_mb = os.path.getsize(model_path) / (1024 * 1024)
            logger.info(" [OK] Model file found: %s (Size: %.2f MB)", model_path, file_size_mb)
        else:
            logger.error(" [FAIL] Model file NOT found at: %s", model_path)
            continue
            
        # 2. Check if JSON config file exists
        if os.path.exists(config_path):
            logger.info(" [OK] Config file found: %s", config_path)
        else:
            logger.error(" [FAIL] Config file NOT found at: %s", config_path)
            continue
            
        # 3. Try loading via Phoonnx
        try:
            logger.info(" Attempting to load voice into memory via TTSVoice.load()...")
            voice = TTSVoice.load(model_path, config_path)
            logger.info(" [SUCCESS] Voice '%s' loaded successfully!", key)
        except Exception as e:
            logger.error(" [EXCEPTION] Failed to load voice '%s'. Error: %s", key, e)

    logger.info("-" * 40)
    logger.info("Diagnostic check complete.")

class MultiSpeakerOonnxService:
    def __init__(self):
        logger.info("Initializing Multi-Speaker Phoonnx Service...")
    
        # Pre-load voices into memory to avoid reloading on every request
        self.loaded_voices = {}
        for key, conf in voices_config.items():

            try:
                logger.info("Loading voice '%s' from %s", conf["name"], conf["model_path"])
                self.loaded_voices[key] = TTSVoice.load(conf["model_path"], conf["config_path"])
                logger.info("Successfully loaded: %s", key)
            except Exception as e:
                logger.error("FAILED to load voice %s from %s. Error: %s", key, conf["model_path"], e)

        self.cfg = SynthesisConfig(
            length_scale=1.2,
            noise_scale=0.667,
            volume=2.0,
        )    

    def get_available_speakers(self):
        return [{"id": k, "name": v["name"]} for k, v in self.voices_config.items() if k in self.loaded_voices]

    def synthesize_to_bytes(self, text, speaker_id="speaker_albrecht", target_sample_rate=None):
        if speaker_id not in self.loaded_voices:
            raise ValueError(f"Speaker ID '{speaker_id}' not found or failed to load.")

        voice = self.loaded_voices[speaker_id]
        logger.info("Synthesizing text with speaker '%s': %s", speaker_id, text)

        # Generate raw WAV from the ONNX model into an in-memory buffer
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file, self.cfg)
            
            wav_buffer.seek(0)
            data, model_sample_rate = sf.read(wav_buffer, dtype="float32")

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

# Initialize multi-speaker service instance
tts_service = MultiSpeakerOonnxService()

# HTML Frontend Template with a Speaker Dropdown
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Speaker Phoonnx TTS Player</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 40px; display: flex; justify-content: center; }
        .card { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 500px; }
        h2 { margin-top: 0; color: #007bff; }
        label { display: block; margin-top: 15px; margin-bottom: 5px; font-weight: bold; }
        select, textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; box-sizing: border-box; }
        textarea { height: 100px; resize: vertical; }
        button { background-color: #007bff; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 4px; cursor: pointer; margin-top: 20px; width: 100%; }
        button:hover { background-color: #0056b3; }
        audio { width: 100%; margin-top: 20px; }
        .loading { font-style: italic; color: #666; margin-top: 10px; display: none; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Multi-Speaker TTS Player</h2>
        
        <label for="speakerSelect">Select Speaker / Voice:</label>
        <select id="speakerSelect">
            <!-- Dynamically populated via JavaScript -->
        </select>

        <label for="textInput">Text to Synthesize:</label>
        <textarea id="textInput">Hallo, mein Name ist Albrecht.</textarea>
        
        <button onclick="synthesizeAndPlay()">Synthesize & Play</button>
        <div id="loadingStatus" class="loading">Synthesizing audio...</div>
        <audio id="audioPlayer" controls></audio>
    </div>

    <script>
        // Fetch available speakers on load to populate dropdown
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
                console.error("Failed to load speakers list", err);
            }
        };

        function synthesizeAndPlay() {
            const text = document.getElementById('textInput').value;
            const speakerId = document.getElementById('speakerSelect').value;
            const audioPlayer = document.getElementById('audioPlayer');
            const loadingStatus = document.getElementById('loadingStatus');

            if (!text.trim()) {
                alert("Please enter some text.");
                return;
            }

            loadingStatus.style.display = 'block';
            
            // Request audio stream with text and selected speaker ID
            const audioUrl = `/say?text=${encodeURIComponent(text)}&speaker=${encodeURIComponent(speakerId)}&t=${Date.now()}`;
            
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
    speaker_id = request.args.get("speaker", "speaker_albrecht")

    if not text:
        return Response("Missing text parameter", status=400)

    try:
        audio_bytes = tts_service.synthesize_to_bytes(text, speaker_id=speaker_id)
        return Response(audio_bytes, mimetype="audio/wav")

    except Exception:
        logger.exception("TTS synthesis failed")
        return Response("TTS synthesis failed", status=500)

if __name__ == "__main__":
    logger.info("Starting Multi-Speaker Flask TTS server on port 5700...")
    test_load_models()
    app.run(host="0.0.0.0", port=5700, use_reloader=False)
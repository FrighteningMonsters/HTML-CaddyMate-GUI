import json
import os
import sqlite3
import threading
import time

try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import vosk
except ImportError:
    vosk = None


class VoiceToText:
    """Real-time local speech recognition using Vosk + sounddevice."""

    def __init__(self, model_path=None, db_path=None, device=None, use_grammar=True):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = model_path or os.path.join(base_dir, "resources", "vosk-model-small-en-us-0.15")
        self.db_path = db_path or os.path.join(base_dir, "data", "caddymate_store.db")
        self.device = device
        self.use_grammar = use_grammar

        self.sample_rate = 44100
        self.block_size = 4000

        self.model = None
        self.recognizer = None
        self.stream = None

        self.stop_event = threading.Event()
        self._lock = threading.Lock()

        self.latest_text = ""
        self.partial_text = ""
        self.final_text = ""
        self.last_error = ""
        self.last_status = ""
        self.last_volume = 0
        self.last_update_ts = 0.0

    def is_available(self):
        return sd is not None and vosk is not None and np is not None

    def availability_error(self):
        missing = []
        if sd is None:
            missing.append("sounddevice")
        if vosk is None:
            missing.append("vosk")
        if np is None:
            missing.append("numpy")

        if missing:
            return f"Missing Python packages: {', '.join(missing)}"

        if not os.path.exists(self.model_path):
            return f"Vosk model folder not found at {self.model_path}"

        return ""

    def _set_error(self, message):
        with self._lock:
            self.last_error = message
            self.last_update_ts = time.time()

    def _clear_error(self):
        with self._lock:
            self.last_error = ""

    def get_items_from_db(self):
        if not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM items")
        items = [row[0].strip().lower() for row in cur.fetchall() if row and row[0]]
        conn.close()

        return sorted(set(filter(None, items)))

    def build_grammar(self, items):
        if not items:
            return None

        all_words = set(items)
        for item in items:
            for word in item.split():
                word = word.replace('(', '').replace(')', '').replace('"', '').replace("'", '').lower()
                for part in word.split('-'):
                    if part:
                        all_words.add(part)

        if not all_words:
            return None

        return json.dumps(sorted(all_words))

    def _build_recognizer(self):
        grammar = None
        if self.use_grammar:
            items = self.get_items_from_db()
            items = [item for item in items if item != "au"]
            grammar = self.build_grammar(items)

        if grammar:
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate, grammar)
        else:
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

        self.recognizer.SetWords(True)

    def load_model(self):
        if self.model:
            return True

        availability_error = self.availability_error()
        if availability_error:
            self._set_error(availability_error)
            return False

        try:
            vosk.SetLogLevel(-1)
            self.model = vosk.Model(self.model_path)
            self._build_recognizer()
            self._clear_error()
            return True
        except Exception as error:
            self._set_error(f"Failed to load Vosk model: {error}")
            return False

    def _reset_runtime_state(self):
        with self._lock:
            self.latest_text = ""
            self.partial_text = ""
            self.final_text = ""
            self.last_status = ""
            self.last_volume = 0
            self.last_update_ts = time.time()

    def start(self, on_result=None):
        with self._lock:
            if self.stream is not None:
                return True

        if not self.load_model():
            return False

        try:
            self._build_recognizer()
        except Exception as error:
            self._set_error(f"Failed to initialize recognizer: {error}")
            return False

        self.stop_event.clear()
        self._reset_runtime_state()

        def audio_callback(indata, frames, time_info, status):
            if self.stop_event.is_set():
                return

            if status:
                with self._lock:
                    self.last_status = str(status)
                    self.last_update_ts = time.time()

            try:
                audio = np.frombuffer(indata, dtype=np.int16)
                volume = int(np.abs(audio).mean()) if audio.size else 0
                data = bytes(indata)
            except Exception as error:
                self._set_error(f"Audio decode failed: {error}")
                return

            with self._lock:
                self.last_volume = volume
                self.last_update_ts = time.time()

            try:
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = (result.get("text") or "").strip()
                    if text:
                        with self._lock:
                            self.latest_text = text
                            self.final_text = text
                            self.partial_text = ""
                            self.last_update_ts = time.time()
                        if on_result:
                            on_result(text, final=True)
                else:
                    partial = json.loads(self.recognizer.PartialResult()).get("partial", "").strip()
                    if partial:
                        with self._lock:
                            self.latest_text = partial
                            self.partial_text = partial
                            self.last_update_ts = time.time()
                        if on_result:
                            on_result(partial, final=False)
            except Exception as error:
                self._set_error(f"Recognizer processing failed: {error}")

        stream_kwargs = {
            "samplerate": self.sample_rate,
            "blocksize": self.block_size,
            "dtype": "int16",
            "channels": 1,
            "callback": audio_callback,
        }

        if self.device is not None:
            stream_kwargs["device"] = self.device

        try:
            self.stream = sd.RawInputStream(**stream_kwargs)
            self.stream.start()
            self._clear_error()
            return True
        except Exception as error:
            with self._lock:
                self.stream = None
            self._set_error(f"Failed to start microphone stream: {error}")
            return False

    def stop(self):
        self.stop_event.set()

        with self._lock:
            stream = self.stream
            self.stream = None

        if stream:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

        final_text = ""
        try:
            if self.recognizer:
                final_text = json.loads(self.recognizer.FinalResult()).get("text", "").strip()
        except Exception as error:
            self._set_error(f"Failed to finalize recognition: {error}")

        if final_text:
            with self._lock:
                self.latest_text = final_text
                self.final_text = final_text
                self.partial_text = ""
                self.last_update_ts = time.time()

        return final_text

    def get_status(self):
        with self._lock:
            return {
                "running": self.stream is not None,
                "text": self.latest_text,
                "partial_text": self.partial_text,
                "final_text": self.final_text,
                "last_error": self.last_error,
                "last_status": self.last_status,
                "last_volume": self.last_volume,
                "last_update_ts": self.last_update_ts,
                "model_loaded": self.model is not None,
                "model_path": self.model_path,
            }

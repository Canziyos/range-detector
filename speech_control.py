import os, time, requests
import torch
import torch.nn.functional as F
import sounddevice, soundfile                           # mic libs kept for later.
from speech_command.model import BitGateNet
from speech_command import preprocess_audio_batch
import numpy as np

# Config.
LABELS     = ["yes", "no", "on", "off", "stop", "go", "_unknown_", "_silence_"]
DEVICE     = "cpu"
MODEL_PATH = "speech_command/ckp/b_m_0.8298.pth"
AUDIO_DIR  = "speech_command/me"
THRESHOLD  = 0.70                                                # confidence required to trigger
CMD_URL    = "http://localhost:5000/status/sendcmd?cmd={}"

# Return to live-mic testing later!
sounddevice.default.device = 1              # may change once mic issue is solved

# Test WAV list
samples = ["stop2.wav", "why.wav", "nej.wav", "go.wav", "fuck.wav", "stap.wav", "yes.wav", "stop2.wav"]

# Model init.
model = BitGateNet(num_classes=len(LABELS), q_en=False).to(DEVICE)
try:
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
except Exception as e:
    print(f"Model load error: {e}")
    exit(1)

# Loop over samples.
for fname in samples:
    wav_path = os.path.join(AUDIO_DIR, fname)

    # 1. Load WAV.
    try:
        waveform_np, sr = soundfile.read(wav_path)
        if waveform_np.ndim > 1:
            waveform_np = waveform_np.mean(axis=1)      # force mono
        waveform = torch.tensor(waveform_np, dtype=torch.float32).unsqueeze(0)
    except Exception as e:
        print(f"[LOAD FAIL] {fname} => {e}")
        continue

    # # resample to 16 kHz
    # if sr != 16000:
    #     import torchaudio
    #     waveform = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=16000)
    #     sr = 16000

    # --- 2. Preprocess --------------------------------------------------------
    batch = [{
        "audio": {"array": waveform.squeeze(0).numpy(), "sampling_rate": sr},
        "label": 0
    }]
    mfcc_tensor, _ = preprocess_audio_batch(batch)
    mfcc = mfcc_tensor.to(DEVICE)

    # 3. Inference.
    with torch.no_grad():
        outputs     = model(mfcc)
        probs       = F.softmax(outputs, dim=1).squeeze()
        pred_idx    = outputs.argmax(dim=1).item()
        pred_label  = LABELS[pred_idx]
        confidence  = probs[pred_idx].item()

    print(f"{fname:<15} => {pred_label:<10} (conf: {confidence:.4f})")

    # 4. Trigger command if confidence high enough.
    try:
        if pred_label == "stop" and confidence >= THRESHOLD:
            resp = requests.post(CMD_URL.format("STOP"), timeout=1)
            print(f"=> sent STOP  | HTTP {resp.status_code} | ok={resp.ok}")
        elif pred_label in {"on", "go", "yes"} and confidence >= THRESHOLD:
            resp = requests.post(CMD_URL.format("START"), timeout=1)
            print(f"=> sent START | HTTP {resp.status_code} | ok={resp.ok}")
    except Exception as e:
        print(f"[HTTP FAIL] {e}")

    time.sleep(2)

# -----------------------------------------------------------------------------
# The commented mic-recording block at top stays for future live testing.

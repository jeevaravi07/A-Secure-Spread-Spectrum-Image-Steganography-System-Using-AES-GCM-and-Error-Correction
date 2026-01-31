"""
stego_encrypt_gui_meta.py
- Select cover image, enter message, enter seed (or leave blank to autogenerate)
- Generates a random 5-digit numeric password, encrypts message with AES-GCM,
  embeds (nonce||tag||ciphertext) into LSBs using FHSS-like hopping,
  saves <cover>_stego.png and <cover>_stego_meta.json and generated_password_<cover>.txt
"""

import os, random, json, binascii
import numpy as np
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256
import customtkinter as ctk
from tkinter import filedialog, messagebox
from math import log10, sqrt

# ---------------- Utilities ----------------
def generate_5digit_password():
    return "{:05d}".format(random.randint(0, 99999))

def derive_key(password: str, key_size=32) -> bytes:
    return SHA256.new(data=password.encode()).digest()[:key_size]

def aes_gcm_encrypt(plaintext: bytes, key: bytes):
    nonce = get_random_bytes(12)            # 12-byte recommended for GCM
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return nonce, tag, ciphertext

def append_crc(data_bytes: bytes) -> bytes:
    crc = binascii.crc32(data_bytes) & 0xffffffff
    return data_bytes + crc.to_bytes(4, byteorder='big')

def image_to_array(path):
    img = Image.open(path).convert('RGB')
    return np.array(img), img.format

def array_to_image(arr, out_path):
    Image.fromarray(arr.astype('uint8'), 'RGB').save(out_path, format='PNG')

def bytes_to_bitstream(b: bytes) -> str:
    return ''.join(f'{byte:08b}' for byte in b)

def mse(a,b):
    return np.mean((a.astype(np.float64)-b.astype(np.float64))**2)

def psnr(a,b):
    m = mse(a,b)
    if m == 0: return float('inf')
    return 20 * log10(255.0 / sqrt(m))

# ---------------- FHSS embedding (deterministic) ----------------
def embed_bits_in_image_fhss(cover_arr: np.ndarray, bitstream: str, channels: list, seed: int):
    h,w,_ = cover_arr.shape
    capacity = h * w * len(channels)
    if len(bitstream) > capacity:
        raise ValueError(f"Not enough capacity: need {len(bitstream)} bits, capacity {capacity}")
    pixel_indices = list(range(h*w))
    rng = random.Random(seed)
    rng.shuffle(pixel_indices)
    out = cover_arr.copy()
    for bit_idx, bit in enumerate(bitstream):
        pix_idx = pixel_indices[bit_idx // len(channels)]
        channel = channels[rng.randrange(len(channels))]
        y = pix_idx // w
        x = pix_idx % w
        out[y,x,channel] = (out[y,x,channel] & 0xFE) | int(bit)
    return out

# ---------------- GUI and flow ----------------
def run_embedding(cover_path, secret_message, seed_input):
    cover_arr, _ = image_to_array(cover_path)
    message_bytes = secret_message.encode('utf-8')
    with_crc = append_crc(message_bytes)

    # generate 5-digit password and derive key
    password = generate_5digit_password()
    key = derive_key(password)

    nonce, tag, ciphertext = aes_gcm_encrypt(with_crc, key)
    payload = nonce + tag + ciphertext
    bitstream = bytes_to_bitstream(payload)

    # seed handling
    if seed_input.strip() == "":
        seed = random.getrandbits(32)
    else:
        seed = int(seed_input.strip(), 0)

    channels = [0,1,2]
    stego_arr = embed_bits_in_image_fhss(cover_arr, bitstream, channels, seed)

    base = os.path.splitext(cover_path)[0]
    stego_path = base + "_stego.png"
    meta_path = base + "_stego_meta.json"
    password_path = f"{base}_generated_password.txt"

    array_to_image(stego_arr, stego_path)

    meta = {
        "seed": seed,
        "channels": channels,
        "bit_len": len(bitstream),   # number of bits embedded
        "cipher": "AES-GCM",
        "nonce_len": 12,
        "tag_len": 16
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    with open(password_path, "w") as f:
        f.write(password)

    stats = {
        "MSE": float(mse(cover_arr, stego_arr)),
        "PSNR": float(psnr(cover_arr, stego_arr))
    }
    return stego_path, meta_path, password, stats

# ---------------- GUI ----------------
def build_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title("Stego Encryption (with meta + auto password)")
    app.geometry("880x640")

    frame_left = ctk.CTkFrame(app, width=320)
    frame_left.pack(side="left", fill="y", padx=12, pady=12)

    frame_right = ctk.CTkFrame(app)
    frame_right.pack(side="right", fill="both", expand=True, padx=12, pady=12)

    # Left controls
    file_var = ctk.StringVar(value="No file selected")
    ctk.CTkLabel(frame_left, text="Cover Image").pack(pady=(8,4))
    ctk.CTkLabel(frame_left, textvariable=file_var, wraplength=280).pack(pady=4)

    def browse_cover():
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if p:
            file_var.set(p)
    ctk.CTkButton(frame_left, text="Browse", command=browse_cover).pack(pady=6)

    ctk.CTkLabel(frame_left, text="Secret Message").pack(pady=(12,4))
    msg_box = ctk.CTkTextbox(frame_left, width=280, height=140)
    msg_box.insert("1.0","Hello from SSIS!")
    msg_box.pack(pady=6)

    ctk.CTkLabel(frame_left, text="Seed (integer, optional)").pack(pady=(8,4))
    seed_entry = ctk.CTkEntry(frame_left, placeholder_text="Leave blank to auto-generate")
    seed_entry.pack(pady=6)

    status = ctk.CTkTextbox(frame_left, width=280, height=160)
    status.pack(pady=8)

    def update_status(text):
        status.delete("1.0","end")
        status.insert("1.0", text)

    # Right: simple plots placeholders and metrics
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    fig_hist = plt.Figure(figsize=(5,3), dpi=100)
    ax_hist = fig_hist.add_subplot(111)
    canvas_hist = FigureCanvasTkAgg(fig_hist, master=frame_right)
    canvas_hist.get_tk_widget().pack(padx=6, pady=6)

    fig_fft = plt.Figure(figsize=(8,3), dpi=100)
    ax_fft = fig_fft.add_subplot(111)
    canvas_fft = FigureCanvasTkAgg(fig_fft, master=frame_right)
    canvas_fft.get_tk_widget().pack(padx=6, pady=6)

    metrics_box = ctk.CTkTextbox(frame_right, width=360, height=120)
    metrics_box.pack(padx=6, pady=6)

    def on_start():
        path = file_var.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error","Select a valid cover image")
            return
        msg = msg_box.get("1.0","end").strip()
        if not msg:
            messagebox.showerror("Error","Message is empty")
            return
        try:
            stego_path, meta_path, password, stats = run_embedding(path, msg, seed_entry.get())
        except Exception as e:
            messagebox.showerror("Error", f"Embedding failed: {e}")
            return

        update_status(f"Embedding complete!\nStego: {stego_path}\nMeta: {meta_path}\nPassword saved to {os.path.splitext(stego_path)[0]}_generated_password.txt\n\nPassword: {password}")
        metrics_box.delete("1.0","end")
        metrics_box.insert("1.0", f"PSNR: {stats['PSNR']:.4f}\\nMSE: {stats['MSE']:.6f}")

        # quick histogram and radial FFT of difference
        cover_arr, _ = image_to_array(path)
        stego_arr, _ = image_to_array(stego_path)
        ax_hist.clear()
        ax_hist.hist(np.mean(cover_arr,axis=2).ravel(), bins=256, alpha=0.6, label='cover')
        ax_hist.hist(np.mean(stego_arr,axis=2).ravel(), bins=256, alpha=0.6, label='stego')
        ax_hist.legend()
        canvas_hist.draw_idle()

        diff = np.mean(stego_arr,axis=2).astype(np.float32) - np.mean(cover_arr,axis=2).astype(np.float32)
        f = np.fft.fftshift(np.fft.fft2(diff))
        mag = np.abs(f)
        cy, cx = np.array(mag.shape)//2
        y, x = np.indices(mag.shape)
        r = np.sqrt((x-cx)**2 + (y-cy)**2).astype(np.int32)
        rbin = np.bincount(r.ravel(), mag.ravel())
        rcount = np.bincount(r.ravel())
        radial = rbin / (rcount + 1e-12)
        ax_fft.clear()
        ax_fft.plot(radial[:min(400, len(radial))])
        canvas_fft.draw_idle()

    ctk.CTkButton(frame_left, text="Start Embedding", command=on_start, fg_color="green").pack(pady=6)

    app.mainloop()

if __name__ == "__main__":
    build_gui()

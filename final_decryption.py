"""
stego_decrypt_gui_meta.py
- Select the stego PNG produced by the encryption script
- It reads the companion <basename>_stego_meta.json to obtain seed/channels/bit_len
- Extracts exactly the embedded bits in the same FHSS sequence
- Reconstructs payload (nonce||tag||ciphertext) and decrypts with password you enter
- Displays message or clear error if authentication fails
"""

import os, json, random, binascii, time
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from math import log10, sqrt

# ---------------- Utilities ----------------
def derive_key(password: str, key_size=32):
    return SHA256.new(data=password.encode()).digest()[:key_size]

def bitstream_to_bytes(bs: str) -> bytes:
    if len(bs) % 8 != 0:
        bs += '0' * (8 - len(bs) % 8)
    return bytes(int(bs[i:i+8], 2) for i in range(0, len(bs), 8))

def extract_bits_from_image_fhss(stego_arr: np.ndarray, bit_len: int, channels: list, seed: int):
    h,w,_ = stego_arr.shape
    capacity = h*w*len(channels)
    if bit_len > capacity:
        raise ValueError(f"Requested bit_len {bit_len} > capacity {capacity}")
    pixel_indices = list(range(h*w))
    rng = random.Random(seed)
    rng.shuffle(pixel_indices)
    bits = []
    for bit_idx in range(bit_len):
        pix_idx = pixel_indices[bit_idx // len(channels)]
        channel = channels[rng.randrange(len(channels))]
        y = pix_idx // w
        x = pix_idx % w
        bits.append(str(stego_arr[y,x,channel] & 1))
    return ''.join(bits)

# ---------------- GUI ----------------
def build_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title("Stego Decryption (meta-aware)")
    app.geometry("1100x700")

    main = ctk.CTkFrame(app)
    main.pack(fill="both", expand=True, padx=12, pady=12)

    left = ctk.CTkFrame(main, width=360)
    left.pack(side="left", fill="y", padx=(0,12))

    right = ctk.CTkFrame(main)
    right.pack(side="right", fill="both", expand=True)

    file_var = ctk.StringVar(value="No file selected")
    ctk.CTkLabel(left, text="Stego image (PNG)").pack(pady=(8,4))
    ctk.CTkLabel(left, textvariable=file_var, wraplength=320).pack(pady=4)

    def browse():
        p = filedialog.askopenfilename(filetypes=[("PNG Image","*.png")])
        if p:
            file_var.set(p)
            path_entry.set(p)
    ctk.CTkButton(left, text="Browse", command=browse).pack(pady=6)

    path_entry = ctk.StringVar(value="")
    path_entry_box = ctk.CTkEntry(left, textvariable=path_entry, width=320)
    path_entry_box.pack(pady=6)

    ctk.CTkLabel(left, text="5-digit Password (from encryption)").pack(pady=(12,4))
    pw_entry = ctk.CTkEntry(left, placeholder_text="Enter 5-digit password")
    pw_entry.pack(pady=6, fill="x")

    start_btn = ctk.CTkButton(left, text="Start Extraction", fg_color="green")
    start_btn.pack(pady=12, fill="x")

    result_box = ctk.CTkTextbox(left, width=320, height=200)
    result_box.pack(pady=8)
    result_box.insert("1.0", "Result will appear here...")

    metrics_box = ctk.CTkTextbox(right, height=120)
    metrics_box.pack(pady=8, fill="x")

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    fig_hist = plt.Figure(figsize=(6,3), dpi=100)
    ax_hist = fig_hist.add_subplot(111)
    canvas_hist = FigureCanvasTkAgg(fig_hist, master=right)
    canvas_hist.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=False)

    fig_fft = plt.Figure(figsize=(8,3), dpi=100)
    ax_fft = fig_fft.add_subplot(111)
    canvas_fft = FigureCanvasTkAgg(fig_fft, master=right)
    canvas_fft.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=True)

    def start_extraction():
        p = path_entry.get().strip()
        if not p or not os.path.exists(p):
            messagebox.showerror("Error","Select a valid stego PNG file")
            return
        base = os.path.splitext(p)[0]
        meta_path = base + "_stego_meta.json"
        if not os.path.exists(meta_path):
            messagebox.showerror("Error", f"Meta JSON not found at {meta_path} (encryption must save meta).")
            return
        try:
            meta = json.load(open(meta_path,"r"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read meta JSON: {e}")
            return

        seed = meta.get("seed")
        channels = meta.get("channels")
        bit_len = meta.get("bit_len")

        if seed is None or channels is None or bit_len is None:
            messagebox.showerror("Error","Meta JSON missing required fields (seed/channels/bit_len)")
            return

        password = pw_entry.get().strip()
        if password == "":
            messagebox.showerror("Error","Enter the 5-digit password generated during encryption.")
            return

        # load stego array
        stego_arr = np.array(Image.open(p).convert("RGB"))
        start_time = time.time()
        try:
            bits = extract_bits_from_image_fhss(stego_arr, bit_len, channels, int(seed))
            payload = bitstream_to_bytes(bits)
            # parse nonce/tag/ciphertext based on meta
            nonce_len = meta.get("nonce_len", 12)
            tag_len = meta.get("tag_len", 16)
            if len(payload) < (nonce_len + tag_len + 1):
                raise ValueError("Extracted payload too small to contain nonce+tag+ciphertext")

            nonce = payload[:nonce_len]
            tag = payload[nonce_len:nonce_len+tag_len]
            ciphertext = payload[nonce_len+tag_len:]

            key = derive_key(password)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext_plus_crc = cipher.decrypt_and_verify(ciphertext, tag)

            # verify CRC appended
            if len(plaintext_plus_crc) < 4:
                raise ValueError("Decrypted payload too short (no CRC)")

            data = plaintext_plus_crc[:-4]
            crc_stored = int.from_bytes(plaintext_plus_crc[-4:], byteorder='big')
            crc_calc = binascii.crc32(data) & 0xffffffff
            if crc_calc != crc_stored:
                raise ValueError("CRC mismatch (data corrupted)")

            try:
                message_text = data.decode('utf-8')
            except:
                message_text = data.hex()

            elapsed = (time.time() - start_time) * 1000.0
            result_box.delete("1.0","end")
            result_box.insert("1.0", f"✅ Decryption successful (time {elapsed:.1f} ms)\\n\\n{message_text}")

            # metrics and simple plots
            metrics_box.delete("1.0","end")
            metrics_box.insert("1.0", f"Elapsed: {elapsed:.1f} ms\\nPayload bytes: {len(payload)}\\nStatus: Success")

            # histogram
            ax_hist.clear()
            gray = np.mean(stego_arr, axis=2).astype(np.uint8).ravel()
            ax_hist.hist(gray, bins=256)
            ax_hist.set_title("Stego Grayscale Histogram")
            canvas_hist.draw_idle()

            # FFT radial avg
            f = np.fft.fftshift(np.fft.fft2(np.mean(stego_arr,axis=2)))
            mag = np.abs(f)
            cy,cx = np.array(mag.shape)//2
            y,x = np.indices(mag.shape)
            r = np.sqrt((x-cx)**2 + (y-cy)**2).astype(np.int32)
            rbin = np.bincount(r.ravel(), mag.ravel())
            rcount = np.bincount(r.ravel())
            radial = rbin / (rcount + 1e-12)
            ax_fft.clear()
            ax_fft.plot(radial[:min(len(radial),400)])
            ax_fft.set_title("FFT Radial Avg (Stego)")
            canvas_fft.draw_idle()

        except ValueError as e:
            result_box.delete("1.0","end")
            result_box.insert("1.0", f"Extraction failed: {e}")
            metrics_box.delete("1.0","end")
            metrics_box.insert("1.0", "Status: Failed")
        except Exception as e:
            result_box.delete("1.0","end")
            result_box.insert("1.0", f"Extraction error: {e}")
            metrics_box.delete("1.0","end")
            metrics_box.insert("1.0", "Status: Error")

    start_btn.configure(command=start_extraction)
    app.mainloop()

if __name__ == "__main__":
    build_gui()

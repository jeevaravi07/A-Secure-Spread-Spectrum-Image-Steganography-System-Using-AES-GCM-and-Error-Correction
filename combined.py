
# Python 3.8

import os, random, json, binascii, time, traceback
import numpy as np
from PIL import Image, ImageTk
from math import log10, sqrt
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Crypto
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256

# Plotting
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Optional libs
try:
    import reedsolo
    REEDS_AVAILABLE = True
except Exception:
    REEDS_AVAILABLE = False

try:
    from skimage.metrics import structural_similarity as ssim
    SSIM_AVAILABLE = True
except Exception:
    SSIM_AVAILABLE = False

try:
    from scipy.signal import wiener
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False

# ---------------- Utilities / Crypto / ECC ----------------
def generate_5digit_password():
    return "{:05d}".format(random.randint(0, 99999))

def derive_key(password: str, key_size=32) -> bytes:
    return SHA256.new(data=password.encode()).digest()[:key_size]

def aes_gcm_encrypt(plaintext: bytes, key: bytes):
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return nonce, tag, ciphertext

def append_crc(data_bytes: bytes) -> bytes:
    crc = binascii.crc32(data_bytes) & 0xffffffff
    return data_bytes + crc.to_bytes(4, byteorder='big')

def rs_encode(payload_bytes: bytes, nsym: int):
    if not REEDS_AVAILABLE:
        raise RuntimeError("reedsolo not available")
    rs = reedsolo.RSCodec(nsym)
    return rs.encode(payload_bytes)

def rs_decode(payload_bytes: bytes, nsym: int):
    if not REEDS_AVAILABLE:
        raise RuntimeError("reedsolo not available")
    rs = reedsolo.RSCodec(nsym)
    decoded = rs.decode(payload_bytes)
    if isinstance(decoded, tuple):
        return decoded[0]
    return decoded

def image_to_array(path):
    img = Image.open(path).convert('RGB')
    return np.array(img), img.format

def array_to_image(arr, out_path):
    Image.fromarray(arr.astype('uint8'), 'RGB').save(out_path, format='PNG')

def bytes_to_bitstream(b: bytes) -> str:
    return ''.join(f'{byte:08b}' for byte in b)

def bitstream_to_bytes(bs: str) -> bytes:
    if len(bs) % 8 != 0:
        bs += '0' * (8 - len(bs) % 8)
    return bytes(int(bs[i:i+8], 2) for i in range(0, len(bs), 8))

def mse(a, b):
    return np.mean((a.astype(np.float64) - b.astype(np.float64))**2)

def psnr(a, b):
    m = mse(a, b)
    if m == 0: return float('inf')
    return 20 * log10(255.0 / sqrt(m))

# Additional metrics helpers
def spatial_correlation(a, b):
    a_flat = np.mean(a, axis=2).ravel().astype(np.float64)
    b_flat = np.mean(b, axis=2).ravel().astype(np.float64)
    if a_flat.std() == 0 or b_flat.std() == 0:
        return 0.0
    return float(np.corrcoef(a_flat, b_flat)[0, 1])

def mean_invariance(a, b):
    ma = float(np.mean(a))
    mb = float(np.mean(b))
    if ma == 0:
        return float('inf') if mb != 0 else 1.0
    return mb / ma

def lsb_change_percent(cover_arr, stego_arr, channels=[0,1,2]):
    # compute percent of LSBs that changed in the chosen channels
    if cover_arr.shape != stego_arr.shape:
        return 0.0
    h,w,_ = cover_arr.shape
    total_bits = h * w * len(channels)
    changed = 0
    for ch in channels:
        cover_lsb = cover_arr[:,:,ch] & 1
        stego_lsb = stego_arr[:,:,ch] & 1
        changed += np.count_nonzero(cover_lsb != stego_lsb)
    return 100.0 * (changed / float(total_bits))

# ---------------- FHSS embedding / extraction (updated to use all channels evenly) ----------------
def embed_bits_in_image_fhss(cover_arr: np.ndarray, bitstream: str, channels: list, seed: int):
  
    h,w,_ = cover_arr.shape
    capacity = h * w * len(channels)
    if len(bitstream) > capacity:
        raise ValueError(f"Not enough capacity: need {len(bitstream)} bits, capacity {capacity}")

    pixel_indices = list(range(h*w))
    rng = random.Random(int(seed))
    rng.shuffle(pixel_indices)

    out = cover_arr.copy()
    bit_idx = 0
    # number of pixels needed
    needed_pixels = (len(bitstream) + len(channels) - 1) // len(channels)
    for pix_order_idx in range(needed_pixels):
        pix_idx = pixel_indices[pix_order_idx]
        y = pix_idx // w
        x = pix_idx % w
        # write up to len(channels) bits into this pixel, in channels order
        for ch in range(len(channels)):
            if bit_idx >= len(bitstream):
                break
            channel = channels[ch]  
            bit = bitstream[bit_idx]
            out[y, x, channel] = (int(out[y, x, channel]) & 0xFE) | int(bit)
            bit_idx += 1

    return out

def extract_bits_from_image_fhss(stego_arr: np.ndarray, bit_len: int,
                                 channels: list, seed: int, mode="direct",
                                 restoration_params=None):
   
    h, w, _ = stego_arr.shape
    capacity = h * w * len(channels)
    if bit_len > capacity:
        raise ValueError(f"Requested bit_len {bit_len} > capacity {capacity}")

    pixel_indices = list(range(h * w))
    rng = random.Random(int(seed))
    rng.shuffle(pixel_indices)

    if restoration_params is None:
        restoration_params = {}
    threshold = restoration_params.get("threshold", 0.5)

    bits = []
    bit_idx = 0
    needed_pixels = (bit_len + len(channels) - 1) // len(channels)

    if mode == "restoration" and SCIPY_AVAILABLE:
        est = np.zeros_like(stego_arr, dtype=np.float32)
        for ch_i in range(3):
            est[:, :, ch_i] = wiener(stego_arr[:, :, ch_i].astype(np.float32), (3, 3))
        est = np.clip(est, 0, 255)
        residual = stego_arr.astype(np.float32) - est
        for pix_order_idx in range(needed_pixels):
            pix_idx = pixel_indices[pix_order_idx]
            y = pix_idx // w
            x = pix_idx % w
            for ch in range(len(channels)):
                if bit_idx >= bit_len:
                    break
                channel = channels[ch]
                bits.append("1" if residual[y, x, channel] > threshold else "0")
                bit_idx += 1
        return "".join(bits)

    # direct mode: read LSBs in same order they were embedded
    for pix_order_idx in range(needed_pixels):
        pix_idx = pixel_indices[pix_order_idx]
        y = pix_idx // w
        x = pix_idx % w
        for ch in range(len(channels)):
            if bit_idx >= bit_len:
                break
            channel = channels[ch]
            bits.append(str(int(stego_arr[y, x, channel] & 1)))
            bit_idx += 1

    return "".join(bits)

# ---------------- Meta helpers ----------------
def write_meta_and_password(base, meta, password):
    meta_path = base + "_stego_meta.json"
    pass_path = base + "_generated_password.txt"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    with open(pass_path, "w") as f:
        f.write(password)
    return meta_path, pass_path

def find_meta_for_stego(stego_path: str):
    base = os.path.splitext(stego_path)[0]
    candidates = [
        base + "_stego_meta.json",
        base + "_meta.json",
        base + "_stego_stego_meta.json",
        base + ".json",
        base + "_stego.json"
    ]
    tried = []
    for c in candidates:
        tried.append(c)
        if os.path.exists(c):
            return c, tried
    return None, tried

def find_generated_password_file(stego_path: str):
    base = os.path.splitext(stego_path)[0]
    candidates = [
        f"{base}_generated_password.txt",
        f"{base}_password.txt",
        f"{base}_generated-pass.txt",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

# ---------------- Core embedding flow ----------------
def run_embedding(cover_path, secret_message, seed_input, use_rs=False, rs_nsym=32, channels=[0,1,2]):
    cover_arr, _ = image_to_array(cover_path)
    message_bytes = secret_message.encode('utf-8')
    with_crc = append_crc(message_bytes)

    password = generate_5digit_password()
    key = derive_key(password)

    nonce, tag, ciphertext = aes_gcm_encrypt(with_crc, key)
    payload = nonce + tag + ciphertext

    rs_applied = False
    if use_rs:
        if REEDS_AVAILABLE:
            try:
                payload = rs_encode(payload, rs_nsym)
                rs_applied = True
            except Exception as e:
                raise RuntimeError(f"Reed-Solomon encoding failed: {e}")
        else:
            raise RuntimeError("RS requested but 'reedsolo' not installed.")

    bitstream = bytes_to_bitstream(payload)

    if str(seed_input).strip() == "":
        seed = random.getrandbits(32)
        autogenerated = True
    else:
        seed = int(str(seed_input).strip(), 0)
        autogenerated = False

    stego_arr = embed_bits_in_image_fhss(cover_arr, bitstream, channels, seed)

    base = os.path.splitext(cover_path)[0]
    stego_path = base + "_stego.png"
    array_to_image(stego_arr, stego_path)

    meta = {
        "seed": int(seed),
        "channels": channels,
        "bit_len": len(bitstream),
        "cipher": "AES-GCM",
        "nonce_len": 12,
        "tag_len": 16,
        "rs_applied": bool(rs_applied),
        "rs_nsym": int(rs_nsym) if rs_applied else 0,
        "autogenerated_seed": bool(autogenerated),
        "cover_path": cover_path  # <-- store original cover so decode can compare
    }

    meta_path, password_path = write_meta_and_password(base, meta, password)

    stats = {
        "MSE": float(mse(cover_arr, stego_arr)),
        "PSNR": float(psnr(cover_arr, stego_arr)),
        "payload_bytes": len(payload),
        "image_shape": cover_arr.shape,
        "spatial_corr": float(spatial_correlation(cover_arr, stego_arr)),
        "mean_invariance": float(mean_invariance(cover_arr, stego_arr)),
        "lsb_change_percent": float(lsb_change_percent(cover_arr, stego_arr, channels))
    }
    return stego_path, meta_path, password, stats

# ---------------- FFT radial helper ----------------
def fft_radial_avg(img_gray):
    f = np.fft.fftshift(np.fft.fft2(img_gray))
    mag = np.abs(f)
    cy, cx = np.array(mag.shape) // 2
    y, x = np.indices(mag.shape)
    r = np.sqrt((x - cx)**2 + (y - cy)**2).astype(np.int32)
    rbin = np.bincount(r.ravel(), mag.ravel())
    rcount = np.bincount(r.ravel())
    radial = rbin / (rcount + 1e-12)
    return radial

# ---------------- GUI ----------------
def build_combined_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title("Spread Spectrum Image Steganography — Combined")
    app.geometry("1200x760")

    top = ctk.CTkFrame(app)
    top.pack(fill="both", expand=True, padx=12, pady=12)

    tab = ctk.CTkTabview(top, width=1160, height=700)
    tab.pack(fill="both", expand=True)
    tab.add("Encode")
    tab.add("Decode")
    tab.set("Encode")

    # ---------------- ENCODE TAB ----------------
    encode_frame = tab.tab("Encode")
    enc_left = ctk.CTkScrollableFrame(encode_frame, width=360)
    enc_left.pack(side="left", fill="y", padx=(12,6), pady=12)
    enc_right = ctk.CTkFrame(encode_frame)
    enc_right.pack(side="right", fill="both", expand=True, padx=(6,12), pady=12)

    enc_file_var = ctk.StringVar(value="No file selected")
    ctk.CTkLabel(enc_left, text="Cover Image").pack(pady=(8,4))
    ctk.CTkLabel(enc_left, textvariable=enc_file_var, wraplength=320).pack(pady=4)

    enc_preview_label = ctk.CTkLabel(enc_left, text="Preview")
    enc_preview_label.pack(pady=6)

    def enc_browse():
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if p:
            enc_file_var.set(p)
            try:
                img = Image.open(p).resize((220,160), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(img)
                enc_preview_label.configure(image=tkimg)
                enc_preview_label.image = tkimg
            except Exception:
                pass

    ctk.CTkButton(enc_left, text="Upload Cover", command=enc_browse).pack(pady=6)
    ctk.CTkLabel(enc_left, text="Secret Message").pack(pady=(12,4))
    enc_msg_box = ctk.CTkTextbox(enc_left, width=320, height=140)
    enc_msg_box.insert("1.0", "Hello from SSIS!")
    enc_msg_box.pack(pady=6)

    ctk.CTkLabel(enc_left, text="Seed (hex/int, optional)").pack(pady=(8,4))
    enc_seed_entry = ctk.CTkEntry(enc_left, placeholder_text="Leave blank to auto-generate")
    enc_seed_entry.pack(pady=6)

    enc_rs_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(enc_left, text="Use Reed-Solomon ECC", variable=enc_rs_var).pack(pady=6)
    enc_rs_nsym = ctk.CTkEntry(enc_left, placeholder_text="RS nsym (e.g. 32)")
    enc_rs_nsym.insert(0, "32")
    enc_rs_nsym.pack(pady=4)

    ctk.CTkLabel(enc_left, text="Channels (0=R,1=G,2=B)").pack(pady=(8,4))
    enc_ch_entry = ctk.CTkEntry(enc_left, placeholder_text="Default: 0,1,2")
    enc_ch_entry.insert(0, "0,1,2")
    enc_ch_entry.pack(pady=6)

    enc_status = ctk.CTkTextbox(enc_left, width=320, height=130)
    enc_status.pack(pady=8)

    # Right plots for encode
    fig_enc_hist = plt.Figure(figsize=(6,3), dpi=100)
    ax_enc_hist = fig_enc_hist.add_subplot(111)
    canvas_enc_hist = FigureCanvasTkAgg(fig_enc_hist, master=enc_right)
    canvas_enc_hist.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=False)

    fig_enc_fft = plt.Figure(figsize=(8,3), dpi=100)
    ax_enc_fft = fig_enc_fft.add_subplot(111)
    canvas_enc_fft = FigureCanvasTkAgg(fig_enc_fft, master=enc_right)
    canvas_enc_fft.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=True)

    # Expanded metrics box
    enc_metrics = ctk.CTkTextbox(enc_right, width=360, height=160)
    enc_metrics.pack(padx=6, pady=6)

    # Encode action
    def on_encode_start():
        try:
            path = enc_file_var.get()
            if not path or not os.path.exists(path):
                messagebox.showerror("Error", "Select a valid cover image")
                return
            msg = enc_msg_box.get("1.0", "end").strip()
            if not msg:
                messagebox.showerror("Error", "Message is empty")
                return

            # parse channels
            ch_text = enc_ch_entry.get().strip()
            try:
                channels = [int(c) for c in ch_text.split(',') if c.strip()!='']
                channels = [c for c in channels if c in (0,1,2)]
                if not channels:
                    channels = [0,1,2]
            except Exception:
                channels = [0,1,2]

            use_rs = bool(enc_rs_var.get())
            rs_nsym = int(enc_rs_nsym.get().strip() or 32)

            start_t = time.time()
            stego_path, meta_path, password, stats = run_embedding(
                path, msg, enc_seed_entry.get(), use_rs=use_rs, rs_nsym=rs_nsym, channels=channels
            )
            elapsed = (time.time() - start_t) * 1000

            enc_status.delete("1.0", "end")
            enc_status.insert("1.0", f" Embedding complete!\nStego: {stego_path}\nMeta: {meta_path}\nPassword saved: {os.path.splitext(stego_path)[0]}_generated_password.txt\n\nPassword: {password}")

            # Build metrics text
            image_shape = stats.get("image_shape", None)
            im_size_str = f"{image_shape[1]}x{image_shape[0]}px" if image_shape is not None else "N/A"
            ssim_val = "N/A"
            try:
                if SSIM_AVAILABLE:
                    cover_arr, _ = image_to_array(path)
                    stego_arr, _ = image_to_array(stego_path)
                    # compute ssim on grayscale
                    ssim_val = ssim(np.mean(cover_arr, axis=2).astype(np.uint8),
                                    np.mean(stego_arr, axis=2).astype(np.uint8))
                    ssim_val = f"{ssim_val:.4f}"
            except Exception:
                ssim_val = "err"

            enc_metrics.delete("1.0", "end")
            enc_metrics.insert("1.0",
                f"Processing Time: {elapsed:.1f} ms\n"
                f"Payload Bytes: {stats.get('payload_bytes')}\n"
                f"Image Size: {im_size_str}\n"
                f"Payload Capacity (bits): {int(image_shape[0]*image_shape[1]*len(channels)) if image_shape else 'N/A'}\n\n"
                f"PSNR: {stats.get('PSNR'):.4f} dB\n"
                f"MSE: {stats.get('MSE'):.6f}\n"
                f"SSIM: {ssim_val}\n"
                f"Spatial Corr: {stats.get('spatial_corr'):.4f}\n"
                f"Mean Invariance: {stats.get('mean_invariance'):.4f}\n"
                f"LSB Change %: {stats.get('lsb_change_percent'):.3f}%\n"
            )

            # plots (box-style histogram bars)
            cover_arr, _ = image_to_array(path)
            stego_arr, _ = image_to_array(stego_path)

            # histogram overlay as bar plots (bolder bars)
            ax_enc_hist.clear()
            cover_gray = np.mean(cover_arr, axis=2).ravel()
            stego_gray = np.mean(stego_arr, axis=2).ravel()

            bins = np.arange(257)  # 256 bins
            cover_counts, _ = np.histogram(cover_gray, bins=bins)
            stego_counts, _ = np.histogram(stego_gray, bins=bins)
            centers = (bins[:-1] + bins[1:]) / 2.0
            bar_width = 0.9  # thick bars

            # Draw background boxed frame
            ax_enc_hist.set_facecolor('#2b2b2b')
            ax_enc_hist.bar(centers - bar_width/4, cover_counts, width=bar_width/2, align='center',
                            label='Cover', color='red', alpha=0.7, edgecolor='black', linewidth=0.3)
            ax_enc_hist.bar(centers + bar_width/4, stego_counts, width=bar_width/2, align='center',
                            label='Stego', color='yellow', alpha=0.6, edgecolor='black', linewidth=0.3)

            ax_enc_hist.set_xlim(0, 255)
            ax_enc_hist.set_title("Histogram Overlay (Encode) — Box Style")
            ax_enc_hist.tick_params(colors='white')
            ax_enc_hist.spines['top'].set_visible(False)
            ax_enc_hist.spines['right'].set_visible(False)
            ax_enc_hist.spines['left'].set_color('white')
            ax_enc_hist.spines['bottom'].set_color('white')
            ax_enc_hist.legend(loc='upper right')
            canvas_enc_hist.draw_idle()

            # FFT radial with larger wave (scale factor to emphasize peaks)
            radial_cover = fft_radial_avg(np.mean(cover_arr, axis=2))
            radial_stego = fft_radial_avg(np.mean(stego_arr, axis=2))

            # Normalize then boost for visual emphasis
            rc = radial_cover.copy()
            rs = radial_stego.copy()
            # avoid division by zero
            rc = rc / (rc.max() + 1e-12)
            rs = rs / (rs.max() + 1e-12)
            scale_factor = 6.0  
            rc *= scale_factor
            rs *= scale_factor

            ax_enc_fft.clear()
            ax_enc_fft.plot(rc[:400], label='Cover', linewidth=2.2, color='red')
            ax_enc_fft.plot(rs[:400], label='Stego', linewidth=2.0, color='blue', alpha=0.9)
            ax_enc_fft.set_ylim(0, max(rc[:400].max(), rs[:400].max()) * 1.15 + 0.01)
            ax_enc_fft.set_title("FFT Radial Avg (Encode) — Emphasized Wave")
            ax_enc_fft.grid(False)
            ax_enc_fft.spines['top'].set_visible(False)
            ax_enc_fft.spines['right'].set_visible(False)
            canvas_enc_fft.draw_idle()

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Embedding failed", str(e))

    ctk.CTkButton(enc_left, text="Start (Encode)", command=on_encode_start, fg_color="green").pack(pady=10)

    # ---------------- DECODE TAB ----------------
    decode_frame = tab.tab("Decode")
    dec_left = ctk.CTkScrollableFrame(decode_frame, width=360)
    dec_left.pack(side="left", fill="y", padx=(12,6), pady=12)
    dec_right = ctk.CTkFrame(decode_frame)
    dec_right.pack(side="right", fill="both", expand=True, padx=(6,12), pady=12)

    dec_file_var = ctk.StringVar(value="No file selected")
    ctk.CTkLabel(dec_left, text="Stego Image").pack(pady=(8,4))
    ctk.CTkLabel(dec_left, textvariable=dec_file_var, wraplength=320).pack(pady=4)

    dec_preview_label = ctk.CTkLabel(dec_left, text="Preview")
    dec_preview_label.pack(pady=6)

    dec_path_entry = ctk.StringVar(value="")
    def dec_browse():
        p = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if p:
            dec_file_var.set(p)
            dec_path_entry.set(p)
            try:
                img = Image.open(p).resize((220,160), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(img)
                dec_preview_label.configure(image=tkimg)
                dec_preview_label.image = tkimg
            except Exception:
                pass
            # try auto-detect password
            pf = find_generated_password_file(p)
            if pf:
                try:
                    with open(pf, 'r') as f:
                        pw_guess = f.read().strip().splitlines()[0]
                    dec_pw_entry.delete(0, 'end')
                    dec_pw_entry.insert(0, pw_guess)
                except Exception:
                    pass

    ctk.CTkButton(dec_left, text="Upload Stego", command=dec_browse).pack(pady=6)
    ctk.CTkEntry(dec_left, textvariable=dec_path_entry, width=320).pack(pady=6)

    ctk.CTkLabel(dec_left, text="Enter 5-digit Password").pack(pady=(8,4))
    dec_pw_entry = ctk.CTkEntry(dec_left, placeholder_text="Password from encryption")
    dec_pw_entry.pack(pady=6, fill="x")

    ctk.CTkLabel(dec_left, text="Extraction Mode").pack(pady=(8,4))
    dec_mode_var = ctk.StringVar(value="direct")
    dec_mode_box = ctk.CTkComboBox(dec_left, values=["direct", "restoration"], variable=dec_mode_var)
    dec_mode_box.pack(pady=6)

    ctk.CTkLabel(dec_left, text="Restoration threshold").pack(pady=(8, 4))
    dec_thresh_entry = ctk.CTkEntry(dec_left, placeholder_text="0.5")
    dec_thresh_entry.insert(0, "0.5")
    dec_thresh_entry.pack(pady=4)

    dec_start_btn = ctk.CTkButton(dec_left, text="Start (Decode)", fg_color="green")
    dec_start_btn.pack(pady=12, fill="x")

    dec_result_box = ctk.CTkTextbox(dec_left, width=320, height=200)
    dec_result_box.pack(pady=8)
    dec_result_box.insert("1.0", "Result will appear here...")

    # Expanded decode metrics
    dec_metrics_box = ctk.CTkTextbox(dec_right, height=180)
    dec_metrics_box.pack(pady=8, fill="x", padx=(6,12))

    # Right plots for decode
    fig_dec_hist = plt.Figure(figsize=(6,3), dpi=100)
    ax_dec_hist = fig_dec_hist.add_subplot(111)
    canvas_dec_hist = FigureCanvasTkAgg(fig_dec_hist, master=dec_right)
    canvas_dec_hist.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=False)

    fig_dec_fft = plt.Figure(figsize=(8,3), dpi=100)
    ax_dec_fft = fig_dec_fft.add_subplot(111)
    canvas_dec_fft = FigureCanvasTkAgg(fig_dec_fft, master=dec_right)
    canvas_dec_fft.get_tk_widget().pack(padx=6, pady=6, fill="both", expand=True)

    # Decode action
    def on_decode_start():
        try:
            p = dec_path_entry.get().strip()
            if not p or not os.path.exists(p):
                messagebox.showerror("Error", "Select a valid stego image")
                return

            meta_path, tried = find_meta_for_stego(p)
            if meta_path is None:
                messagebox.showerror("Error", "Meta JSON not found.\nTried:\n" + "\n".join(tried))
                return

            meta = json.load(open(meta_path, "rb"))
            seed = meta.get("seed")
            bit_len = meta.get("bit_len")
            channels = meta.get("channels", [0,1,2])
            if seed is None:
                raise ValueError("Meta missing 'seed'")
            if bit_len is None:
                raise ValueError("Meta missing 'bit_len'")

            seed = int(seed)
            bit_len = int(bit_len)
            try:
                channels = [int(c) for c in channels]
            except Exception:
                channels = [0,1,2]

            pw = dec_pw_entry.get().strip()
            if pw == "":
                pf = find_generated_password_file(p)
                if pf:
                    try:
                        with open(pf, "r") as f:
                            pw = f.read().strip().splitlines()[0]
                            messagebox.showinfo("Password auto-detected", f"Using password from: {pf}")
                            dec_pw_entry.insert(0, pw)
                    except Exception:
                        pass

            if pw == "":
                messagebox.showerror("Error", "Enter password (or ensure *_generated_password.txt exists).")
                return

            arr = np.array(Image.open(p).convert("RGB"))
            mode = dec_mode_var.get()
            threshold = float(dec_thresh_entry.get().strip() or 0.5)
            restoration_params = {"threshold": threshold}

            # capacity check
            h,w,_ = arr.shape
            cap = h * w * len(channels)
            if bit_len > cap:
                raise ValueError(f"Meta bit_len {bit_len} > image capacity {cap}. Wrong meta or channels/seed mismatch.")

            start_t = time.time()
            bits = extract_bits_from_image_fhss(arr, bit_len, channels, int(seed),
                                                mode=mode, restoration_params=restoration_params)
            payload = bitstream_to_bytes(bits)

            rs_applied = bool(meta.get("rs_applied", False))
            if rs_applied:
                if not REEDS_AVAILABLE:
                    raise RuntimeError("Reed-Solomon required but not installed.")
                rs_nsym = int(meta.get("rs_nsym", 0))
                payload = rs_decode(payload, rs_nsym)

            nonce_len = int(meta.get("nonce_len", 12))
            tag_len = int(meta.get("tag_len", 16))
            if len(payload) < nonce_len + tag_len + 1:
                raise ValueError(f"Payload too small for AES-GCM components: have {len(payload)} bytes, need at least {nonce_len+tag_len+1}.")

            nonce = payload[:nonce_len]
            tag = payload[nonce_len:nonce_len + tag_len]
            ciphertext = payload[nonce_len + tag_len:]

            key = derive_key(pw)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

            try:
                plaintext_plus_crc = cipher.decrypt_and_verify(ciphertext, tag)
            except ValueError as e:
                raise ValueError("MAC check failed during AES-GCM verification. Possible causes: wrong password, corrupted or truncated payload, or RS decode issues.") from e

            if len(plaintext_plus_crc) < 4:
                raise ValueError("Decrypted payload too short (no CRC)")

            data = plaintext_plus_crc[:-4]
            crc_stored = int.from_bytes(plaintext_plus_crc[-4:], 'big')
            crc_calc = binascii.crc32(data) & 0xffffffff
            if crc_calc != crc_stored:
                raise ValueError("CRC mismatch — wrong password or corrupted data")

            msg = data.decode("utf-8", errors="ignore")
            elapsed = (time.time() - start_t) * 1000

            dec_result_box.delete("1.0", "end")
            dec_result_box.insert("1.0", f" Decryption OK ({elapsed:.1f} ms)\n\n{msg}")

            # Metrics display
            dec_metrics_box.delete("1.0", "end")
            payload_post_rs = len(payload)
            rs_flag = rs_applied
            meta_name = os.path.basename(meta_path)
            image_size_str = f"{w}x{h}px"
            metrics_text = [
                f"Elapsed: {elapsed:.1f} ms",
                f"Payload (post-RS): {payload_post_rs} bytes",
                f"RS applied: {rs_flag}",
                f"Meta: {meta_name}",
                f"Image Size: {image_size_str}",
                f"Channels used: {','.join(str(c) for c in channels)}"
            ]

            # try to compute comparison metrics if cover available in meta
            cover_path = meta.get("cover_path")
            if cover_path and os.path.exists(cover_path):
                try:
                    cover_arr, _ = image_to_array(cover_path)
                    # compute MSE/PSNR/SSIM if possible
                    mmse = mse(cover_arr, arr)
                    mpsnr = psnr(cover_arr, arr)
                    ssim_val = "N/A"
                    if SSIM_AVAILABLE:
                        try:
                            ssim_val = ssim(np.mean(cover_arr, axis=2).astype(np.uint8),
                                            np.mean(arr, axis=2).astype(np.uint8))
                            ssim_val = f"{ssim_val:.4f}"
                        except Exception:
                            ssim_val = "err"
                    sp_corr = spatial_correlation(cover_arr, arr)
                    mean_inv = mean_invariance(cover_arr, arr)
                    lsb_pct = lsb_change_percent(cover_arr, arr, channels)
                    metrics_text += [
                        "",
                        f"MSE: {mmse:.6f}",
                        f"PSNR: {mpsnr:.4f} dB",
                        f"SSIM: {ssim_val}",
                        f"Spatial Corr: {sp_corr:.4f}",
                        f"Mean Invariance: {mean_inv:.4f}",
                        f"LSB Change %: {lsb_pct:.3f}%"
                    ]
                except Exception:
                    metrics_text += ["", "Comparison: failed to load cover for comparison"]
            else:
                metrics_text += ["", "Comparison: original cover not found (meta missing or file deleted)"]

            dec_metrics_box.insert("1.0", "\n".join(metrics_text))

            # Decryption histogram — box style, cyan
            ax_dec_hist.clear()
            gray = np.mean(arr, axis=2).ravel()
            bins = np.arange(257)
            dec_counts, _ = np.histogram(gray, bins=bins)
            centers = (bins[:-1] + bins[1:]) / 2.0
            ax_dec_hist.set_facecolor('#2b2b2b')
            ax_dec_hist.bar(centers, dec_counts, width=0.9, align='center',
                            color='cyan', alpha=0.8, edgecolor='black', linewidth=0.25)
            ax_dec_hist.set_xlim(0, 255)
            ax_dec_hist.set_title("Stego Grayscale Histogram (Decode) — Box Style")
            ax_dec_hist.tick_params(colors='white')
            ax_dec_hist.spines['top'].set_visible(False)
            ax_dec_hist.spines['right'].set_visible(False)
            canvas_dec_hist.draw_idle()

            # FFT radial (cyan) with emphasized amplitude
            radial = fft_radial_avg(np.mean(arr, axis=2))
            r = radial.copy()
            r = r / (r.max() + 1e-12)
            r *= 6.0  # same boost to emphasize wave
            ax_dec_fft.clear()
            ax_dec_fft.plot(r[:400], linewidth=2.2, color='cyan')
            ax_dec_fft.set_ylim(0, r[:400].max() * 1.15 + 0.01)
            ax_dec_fft.set_title("FFT Radial Avg (Stego) — Emphasized Wave")
            ax_dec_fft.spines['top'].set_visible(False)
            ax_dec_fft.spines['right'].set_visible(False)
            canvas_dec_fft.draw_idle()

        except Exception as e:
            traceback.print_exc()
            dec_result_box.delete("1.0", "end")
            dec_result_box.insert("1.0", f" Failed: {e}")
            dec_metrics_box.delete("1.0", "end")
            dec_metrics_box.insert("1.0", "Status: Failed")

    dec_start_btn.configure(command=on_decode_start)
    app.bind("<Return>", lambda e: None)
    app.mainloop()

if __name__ == "__main__":
    build_combined_gui()

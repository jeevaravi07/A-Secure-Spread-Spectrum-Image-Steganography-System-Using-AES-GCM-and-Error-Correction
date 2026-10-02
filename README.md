🔐 Spread Spectrum Image Steganography

<p align="center">
  <b>AES-GCM Encrypted Image Steganography with FHSS-Like LSB Embedding, Reed-Solomon ECC, and Visual Quality Analysis</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/AES--GCM-Authenticated%20Encryption-8A2BE2?style=for-the-badge" alt="AES-GCM">
  <img src="https://img.shields.io/badge/Steganography-LSB%20%2B%20FHSS-00A67E?style=for-the-badge" alt="Steganography">
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-1F6FEB?style=for-the-badge" alt="CustomTkinter">
</p>

📌 Overview

Spread Spectrum Image Steganography is a desktop-based Python application for securely hiding a secret text message inside an RGB image.

The application combines:

🔐 AES-GCM authenticated encryption

🖼️ LSB image steganography

📡 FHSS-like deterministic pixel hopping

🛡️ CRC integrity verification

🧩 Optional Reed-Solomon error-correcting code

📊 PSNR, MSE, SSIM and statistical image-quality analysis

📈 Histogram and FFT radial analysis

🖥️ CustomTkinter graphical user interface

🔑 Automatically generated 5-digit encryption password

🔄 Direct and restoration-based extraction modes

The implementation is designed so that the message is encrypted before it is embedded into the image. The decoder reconstructs the same deterministic embedding sequence using the metadata seed and extracts the encrypted payload.

✨ Key Features

Feature

Description

🔐 AES-GCM

Encrypts the secret message and provides authenticated decryption

🔑 5-Digit Password

Generates a random numeric password for each encoding operation

🧬 SHA-256 Key Derivation

Derives a 256-bit AES key from the generated password

🖼️ LSB Embedding

Stores encrypted payload bits in image least-significant bits

📡 FHSS-Like Hopping

Uses a seeded shuffled pixel sequence for deterministic embedding

🎨 RGB Channel Selection

Supports R, G and B channel selection

🛡️ CRC32

Verifies the integrity of the decrypted message

🧩 Reed-Solomon ECC

Optional error-correction layer using reedsolo

🔧 Restoration Mode

Optional Wiener-filter-based extraction mode

📊 Image Metrics

Calculates MSE, PSNR, SSIM, spatial correlation and mean invariance

📉 LSB Analysis

Measures percentage of changed LSBs

📈 Histogram

Visualizes grayscale intensity distribution

🌐 FFT Analysis

Displays radial FFT characteristics of the image

🗂️ Metadata

Stores seed, channels, payload length and encryption parameters

🖥️ GUI

Provides separate Encode and Decode tabs

🧊 3D-Style System Architecture

The following layered architecture represents the project as a 3D-style security pipeline:

                         ┌──────────────────────────────────────┐
                        /   🖥️ USER / GUI LAYER                /|
                       /  CustomTkinter Encode / Decode        / |
                      └──────────────────────────────────────┘  |
                      |                                        | |
                      |   ┌────────────────────────────────┐   | |
                      |  /  🔐 CRYPTOGRAPHIC LAYER        /|   | |
                      | /  Password → SHA-256 → AES-GCM   / |   | |
                      |└────────────────────────────────┘  |   | |
                      |                                     |   | 
                      |   ┌────────────────────────────────┐|   |
                      |  /  📡 STEGANOGRAPHIC LAYER       / |   |
                      | /  Seeded Pixel Shuffle + LSB    /  |   |
                      |└────────────────────────────────┘   |   |
                      |                                      |   |
                      |   ┌────────────────────────────────┐ |  /
                      |  /  🛡️ INTEGRITY / ECC LAYER      /| | /
                      | /  CRC32 + Reed-Solomon          / | |/
                      |└────────────────────────────────┘  |/
                      └──────────────────────────────────────┘

                              ENCODED PNG
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  🔓 DECODE PIPELINE │
                       └─────────────────────┘
                                  │
                  Metadata + Seed + Password
                                  │
                                  ▼
                     Extract Embedded Bitstream
                                  │
                                  ▼
                       Reed-Solomon Decode
                                  │
                                  ▼
                         AES-GCM Verification
                                  │
                                  ▼
                            CRC Verification
                                  │
                                  ▼
                         🔓 Original Message

🔄 Processing Workflow

flowchart TD
    A[🖼️ Cover Image] --> B[Secret Message]
    B --> C[Append CRC32]
    C --> D[Generate 5-Digit Password]
    D --> E[SHA-256 Key Derivation]
    E --> F[AES-GCM Encryption]
    F --> G[Nonce + Tag + Ciphertext]
    G --> H{Optional Reed-Solomon}
    H --> I[Convert Payload to Bits]
    I --> J[Seeded Pixel Shuffle]
    J --> K[LSB Embedding]
    K --> L[🖼️ Stego PNG]
    L --> M[Metadata JSON]

    L --> N[Decode]
    M --> N
    N --> O[Extract Bits]
    O --> P{RS Applied?}
    P -->|Yes| Q[Reed-Solomon Decode]
    P -->|No| R[Encrypted Payload]
    Q --> R
    R --> S[AES-GCM Decryption]
    S --> T[CRC32 Verification]
    T --> U[🔓 Recovered Message]

🔐 Security Pipeline

Secret Message
      │
      ▼
┌───────────────┐
│    CRC32      │
│ Integrity Tag │
└───────┬───────┘
        │
        ▼
┌───────────────────┐
│    AES-GCM        │
│ Encryption        │
│ + Authentication  │
└─────────┬─────────┘
          │
          ▼
┌──────────────────────┐
│ Optional Reed-Solomon│
│ Error Correction     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Bitstream Conversion │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Seeded Pixel Shuffle │
│ FHSS-like Selection  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ RGB LSB Embedding    │
└──────────┬───────────┘
           │
           ▼
       Stego PNG

🧠 Methodology

1. Message Preparation

The user enters a secret text message through the GUI. The message is converted into UTF-8 bytes.

A CRC32 checksum is appended to the message before encryption:

Message + CRC32

This allows the decoder to detect corruption or incorrect recovered data.

2. Password Generation

The encoder generates a random five-digit numeric password.

Example:

Generated Password: 58321

The password is used to derive the AES key.

Security note: A five-digit password has a relatively small search space. This implementation is intended primarily as an academic/project demonstration. For production-grade security, a high-entropy randomly generated secret should be used.

3. SHA-256 Key Derivation

The password is processed using SHA-256 to produce a 32-byte key.

5-Digit Password
       ↓
     SHA-256
       ↓
  256-bit AES Key

4. AES-GCM Encryption

The CRC-protected message is encrypted using AES-GCM.

The resulting encrypted payload consists of:

Nonce || Authentication Tag || Ciphertext

AES-GCM also authenticates the ciphertext, allowing the decoder to detect an incorrect password or modified encrypted payload.

5. Reed-Solomon Error Correction

Reed-Solomon encoding can optionally be enabled through the GUI.

This adds redundancy to the encrypted payload and can help recover data in the presence of certain errors.

The feature depends on:

reedsolo

6. FHSS-Like LSB Embedding

The implementation uses a deterministic shuffled pixel sequence generated from a seed.

Seed
 ↓
Random Number Generator
 ↓
Shuffle Pixel Indices
 ↓
Select Pixels
 ↓
Write Payload Bits to RGB LSBs

The same seed and channel configuration are stored in the metadata JSON so that the decoder can reproduce the extraction order.

The implementation is FHSS-like rather than a radio-frequency FHSS implementation: it applies deterministic hopping/shuffling to image pixel locations.

7. Metadata Generation

The encoder saves a JSON metadata file containing information such as:

{
  "seed": 123456789,
  "channels": [0, 1, 2],
  "bit_len": 1024,
  "cipher": "AES-GCM",
  "nonce_len": 12,
  "tag_len": 16,
  "rs_applied": false,
  "rs_nsym": 0
}

This information is required by the decoder to reconstruct the embedding configuration.

📊 Image Quality Analysis

The application evaluates the visual effect of embedding using multiple measurements.

MSE — Mean Squared Error

Measures the average squared difference between the cover and stego images.

MSE = mean((Cover - Stego)²)

Lower MSE generally indicates smaller pixel-level modification.

PSNR — Peak Signal-to-Noise Ratio

Measures the similarity between the original cover and stego image in decibels.

PSNR = 20 × log10(255 / √MSE)

Higher PSNR indicates lower reconstruction distortion.

SSIM

If scikit-image is installed, the application calculates Structural Similarity Index Measure.

Spatial Correlation

Measures the correlation between the grayscale representations of the cover and stego images.

Mean Invariance

Compares the mean pixel intensity of the cover and stego images.

LSB Change Percentage

Calculates how many selected least-significant bits differ between the cover and stego image.

📈 Visualization Module

The GUI provides visual analysis after encoding and decoding.

Histogram Analysis

The encoder displays an overlay of cover and stego grayscale distributions.

Cover Image  ──────► Histogram
Stego Image  ──────► Histogram
                         │
                         ▼
                 Distribution Comparison

FFT Radial Analysis

The application computes the 2D FFT and radial average of the image spectrum.

Image
  ↓
Grayscale
  ↓
2D FFT
  ↓
FFT Shift
  ↓
Magnitude Spectrum
  ↓
Radial Averaging
  ↓
Frequency-Domain Plot

These visualizations help inspect the effect of embedding in both spatial and frequency domains.

🖥️ GUI Structure

The application contains two main tabs:

🔵 Encode

Upload cover image

Enter secret message

Enter optional seed

Enable/disable Reed-Solomon ECC

Configure RS symbols

Select RGB channels

Start encoding

View generated password

View stego image path

View metadata path

View image-quality metrics

View histogram

View FFT radial analysis

🟢 Decode

Upload stego image

Load metadata

Enter or automatically detect password

Select extraction mode

Configure restoration threshold

Start decoding

Extract encrypted payload

Apply optional Reed-Solomon decoding

Perform AES-GCM authentication

Verify CRC32

Display recovered message

Display decoding metrics

Display histogram and FFT analysis

📁 Output Files

After encoding, the application generates files similar to:

project/
│
├── cover.png
│
├── cover_stego.png
├── cover_stego_meta.json
└── cover_generated_password.txt

*_stego.png

Contains the hidden encrypted message.

*_stego_meta.json

Contains the embedding configuration required for decoding.

*_generated_password.txt

Contains the generated encryption password.

Keep the password file and metadata protected if the hidden message is intended to remain confidential.

🧰 Technologies Used

Technology

Purpose

Python

Core implementation

NumPy

Image-array and numerical operations

Pillow

Image loading and saving

PyCryptodome

AES-GCM encryption and SHA-256

CustomTkinter

Desktop GUI

Matplotlib

Histogram and FFT visualization

Reedsolo

Optional Reed-Solomon ECC

scikit-image

Optional SSIM calculation

SciPy

Optional Wiener restoration

📦 Installation

1. Clone the repository

git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY

2. Create a virtual environment

Windows

python -m venv venv
venv\Scripts\activate

Linux / macOS

python3 -m venv venv
source venv/bin/activate

3. Install required packages

pip install numpy pillow pycryptodome customtkinter matplotlib

4. Install optional packages

For Reed-Solomon ECC:

pip install reedsolo

For SSIM:

pip install scikit-image

For restoration mode:

pip install scipy

Or install all project dependencies together:

pip install numpy pillow pycryptodome customtkinter matplotlib reedsolo scikit-image scipy

▶️ Running the Application

Save the main Python program, for example:

stego_app.py

Run:

python stego_app.py

The application opens a graphical interface containing:

┌───────────────────────────────────────────────┐
│ Spread Spectrum Image Steganography           │
├───────────────────────────────────────────────┤
│   Encode              │       Decode           │
│                       │                        │
│   Cover Image         │   Stego Image          │
│   Secret Message      │   Password             │
│   Seed                │   Extraction Mode      │
│   Reed-Solomon        │   Restoration          │
│   RGB Channels        │   Result               │
│                       │                        │
│   Metrics + Graphs    │   Metrics + Graphs     │
└───────────────────────────────────────────────┘

🧪 Example Workflow

Encoding

Cover Image:
    photo.png

Secret Message:
    Hello from secure steganography!

Seed:
    Auto-generated

Channels:
    0,1,2

Reed-Solomon:
    Enabled / Disabled

The application generates:

photo_stego.png
photo_stego_meta.json
photo_generated_password.txt

Decoding

Use:

photo_stego.png
        +
photo_stego_meta.json
        +
5-digit password

The application extracts and decrypts the payload and displays the original message.

🔍 Extraction Modes

Direct Mode

The decoder directly reads the LSBs from the deterministic pixel sequence.

Stego Image
     ↓
Seeded Pixel Order
     ↓
RGB LSB Extraction
     ↓
Encrypted Payload

Restoration Mode

When SciPy is available, the application estimates image content using a Wiener filter and uses the residual signal for extraction.

Stego Image
     ↓
Wiener Filtering
     ↓
Estimated Image
     ↓
Residual
     ↓
Threshold Decision
     ↓
Recovered Bits

The restoration threshold can be configured through the GUI.

⚙️ Configuration

RGB Channels

0 = Red
1 = Green
2 = Blue

Default:

0,1,2

Examples:

0

or

0,2

or

0,1,2

Seed

The seed may be:

Decimal:
123456789

or a Python-compatible integer representation such as:

0x12345678

If the seed field is left empty, a random 32-bit seed is generated.

📐 Capacity

For an RGB image using three channels, the theoretical LSB capacity is:

Image Height × Image Width × Number of Channels

For example:

1920 × 1080 × 3

gives:

6,220,800 bits

or approximately:

777,600 bytes

The actual usable payload is lower because AES-GCM, metadata configuration and optional error-correction introduce overhead.

🔒 Security Considerations

This project combines encryption and steganography, but these layers provide different protections:

AES-GCM
   ↓
Protects message confidentiality + authentication

Steganography
   ↓
Conceals the existence of the encrypted payload

Important considerations:

The generated five-digit password has limited entropy.

The password is saved in a local text file by the current implementation.

The metadata JSON exposes the embedding seed and configuration.

The stego image should preferably remain in PNG format to avoid lossy JPEG recompression.

The decoder requires compatible metadata, seed, channel configuration and password.

The implementation is intended for educational/research use rather than as a production cryptographic protocol.

For stronger security, a production implementation should use a high-entropy secret and a password-based KDF such as Argon2id, scrypt or PBKDF2 with an appropriate salt.

📂 Suggested Repository Structure

Spread-Spectrum-Steganography/
│
├── stego_app.py
├── README.md
├── requirements.txt
├── .gitignore
│
├── examples/
│   ├── cover.png
│   └── stego.png
│
├── results/
│   ├── histogram/
│   └── fft/
│
└── docs/
    └── project_report.pdf

Do not commit private generated password files or sensitive stego outputs to a public repository.

Recommended .gitignore entries:

__pycache__/
*.pyc
venv/
.env

*_generated_password.txt
*_stego.png
*_stego_meta.json

results/

📊 Evaluation Parameters

The project can be evaluated using:

┌──────────────────────────────┐
│ Image Quality                │
├──────────────────────────────┤
│ MSE                          │
│ PSNR                         │
│ SSIM                         │
│ Spatial Correlation          │
│ Mean Invariance              │
│ LSB Change Percentage        │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Security / Recovery          │
├──────────────────────────────┤
│ AES-GCM Authentication       │
│ CRC32 Integrity Verification │
│ Correct Password Recovery    │
│ Wrong Password Rejection     │
│ Payload Extraction           │
│ Optional Reed-Solomon        │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Performance                  │
├──────────────────────────────┤
│ Encoding Time                │
│ Decoding Time                │
│ Payload Size                 │
│ Image Capacity               │
└──────────────────────────────┘

🚨 Error Handling

The decoder reports failures such as:

Meta JSON not found
Wrong password
AES-GCM MAC check failed
CRC mismatch
Payload too small
Image capacity exceeded
Reed-Solomon package missing
Corrupted or truncated payload

This helps distinguish configuration errors from payload-integrity failures.

🎯 Applications

Potential academic and research applications include:

Secure image-based communication

Confidential message transmission

Multimedia security research

Image steganography experiments

Cryptography and information-security demonstrations

Error-resilient data hiding

Spatial-domain steganography research

Frequency-domain analysis of stego images

Comparative evaluation of image-quality metrics

🚀 Future Enhancements

Possible extensions include:

🔐 Argon2id/scrypt-based password derivation

🔑 High-entropy cryptographic key generation

🧂 Salt and nonce management improvements

📦 Automatic payload-capacity estimation

🖼️ Batch image processing

📊 Automated metric comparison across multiple images

🧠 CNN-based steganalysis

🔍 Advanced statistical steganalysis

🌐 Web-based deployment

📱 Mobile-compatible interface

📈 BER and robustness testing

🧪 JPEG/noise/cropping attack simulations

🗃️ Encrypted metadata storage

👨‍💻 Project Workflow Summary

                 ┌───────────────┐
                 │  Cover Image  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Secret Message│
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │    CRC32      │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   AES-GCM     │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Optional RS   │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Bit Conversion│
                 └───────┬───────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Seeded Pixel Shuffle │
              └──────────┬───────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ RGB LSB     │
                  │ Embedding   │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  Stego PNG  │
                  └──────┬──────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Decode / Extract│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ AES-GCM Verify  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ CRC32 Verify    │
                └────────┬────────┘
                         │
                         ▼
                  🔓 Secret Message

⭐ Project Highlights

Encrypted before embedding.
Deterministic seeded pixel traversal.
LSB-based RGB data hiding.
Optional Reed-Solomon error correction.
AES-GCM authentication.
CRC32 integrity validation.
PSNR, MSE, SSIM and statistical evaluation.
Histogram and FFT visualization.
CustomTkinter desktop interface.

📜 License

This project can be released under the MIT License if that matches your intended repository licensing.

👤 Author

Jeeva R

Computer Science & Engineering
Machine Learning • Computer Vision • Cybersecurity • AI

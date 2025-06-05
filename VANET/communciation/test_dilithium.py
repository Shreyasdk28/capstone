import sys
import os

# Add the directory containing dilithium.pyd to sys.path
module_dir = r'D:\PROJECTS\CAPSTONE\VANET\communciation\dilithium\ref'
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

import dilithium

# Rest of your test code...

# Key generation
pk, sk = dilithium.keygen()
print(f"Public key: {pk[:16]}...")
print(f"Secret key: {sk[:16]}...")

# Signing
msg = b"Hello quantum world!"
sig = dilithium.sign(sk, msg)
print(f"Signature: {sig[:16]}...")

# Verification (placeholder - implement using reference code)
print("Signature length:", len(sig))

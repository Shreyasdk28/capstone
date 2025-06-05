import dilithium

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

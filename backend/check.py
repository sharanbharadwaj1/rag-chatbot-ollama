import sys
import os

print("--- Python's Search Path (sys.path) ---")
for path in sys.path:
    print(path)

print("\n--- Current Working Directory ---")
print(os.getcwd())
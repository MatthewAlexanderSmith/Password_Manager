import hashlib
import os

INPUT_PATH  = os.path.join("..", "data", "rockyou.txt")
OUTPUT_PATH = os.path.join("..", "data", "hibp_sample.txt")
MAX_ENTRIES = 1_000_000

def convert(input_path: str, output_path: str, max_entries: int):
    print(f"Converting {max_entries:,} passwords to SHA-1...")
    count = 0
    with open(input_path, "r", encoding="latin-1") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if count >= max_entries:
                break
            pw = line.strip()
            if pw:
                sha1 = hashlib.sha1(pw.encode("utf-8")).hexdigest().upper()
                fout.write(f"{sha1}:1\n")
                count += 1

    print(f"Done — {count:,} hashes written to {output_path}")

if __name__ == "__main__":
    convert(INPUT_PATH, OUTPUT_PATH, MAX_ENTRIES)
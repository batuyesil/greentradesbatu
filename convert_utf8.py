import os

POSSIBLE_ENCODINGS = ["utf-8", "windows-1254", "windows-1252", "iso-8859-9"]

def convert_file_to_utf8(path):
    for enc in POSSIBLE_ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ UTF-8 yapıldı: {path} (kaynak: {enc})")
            return
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"❌ Hata ({path}): {e}")
            return
    print(f"⚠️ Okunamadı (encoding bulunamadı): {path}")

def walk_and_convert(root="."):
    for root_dir, _, files in os.walk(root):
        for file in files:
            if file.endswith(".py"):
                convert_file_to_utf8(os.path.join(root_dir, file))

if __name__ == "__main__":
    walk_and_convert(".")

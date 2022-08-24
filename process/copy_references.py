import os
import shutil

source = "C:/Users/u12161/Zotero"
dest = r"C:\Users\u12161\OneDrive - Geoscience Australia\References"

for root, dirs, files in os.walk(source):
    for name in [f for f in files if f.endswith("pdf")]:
        if not os.path.exists(os.path.join(dest, name)):
            print(f"Moving {name} to {dest}")
            shutil.copy2(os.path.join(root, name), dest)


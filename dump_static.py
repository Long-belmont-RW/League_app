import os

root = "/opt/render/project/src/staticfiles"

for path, dirs, files in os.walk(root):
    for name in files:
        print(os.path.join(path, name))
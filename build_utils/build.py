import os

def build_lambda(path: str):
    print(f"Starting build: {path}")
    os.system(f"source build_utils/build.sh && build {path}")
    return
import os

def build_lambda(path: str):
    os.system(f"source build_utils/build.sh && build {path}")
    return
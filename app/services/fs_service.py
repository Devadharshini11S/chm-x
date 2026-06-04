import os
from dataclasses import dataclass
from typing import List

@dataclass
class FileInfo:
    path: str
    file_type: str

def detect_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
        return "image"
    if ext in [".txt", ".md", ".rtf"]:
        return "text"
    if ext == ".pdf":
        return "pdf"
    return "other"

def list_files(root_path: str) -> List[FileInfo]:
    files: List[FileInfo] = []
    for dirpath, _, filenames in os.walk(root_path):
        for name in filenames:
            full = os.path.join(dirpath, name)
            files.append(FileInfo(path=full, file_type=detect_type(full)))
    return files

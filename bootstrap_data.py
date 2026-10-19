"""Extract the bundled synthetic research artifacts on first launch."""
from pathlib import Path
import hashlib
import zipfile
ROOT=Path(__file__).resolve().parent
EXPECTED_SHA256="6b1d9ff4dc94d003512797236db85c5171d04592135362a300399324d6319899"
def ensure_data():
    marker=ROOT/'.research_data_ready'
    if marker.is_file() and marker.read_text().strip()==EXPECTED_SHA256:
        return
    archive=ROOT/'research_data.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=EXPECTED_SHA256:
        raise RuntimeError('Research archive checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target=(ROOT/member.filename).resolve()
            if not target.is_relative_to(ROOT):
                raise ValueError('Unsafe research archive path')
        zipped.extractall(ROOT)
    marker.write_text(EXPECTED_SHA256+'\n')
if __name__=='__main__':
    ensure_data()

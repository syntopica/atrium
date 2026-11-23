"""A model and its external data must resolve to one directory.

Found 2026-11-23 on a fresh machine: huggingface-hub 2.2 stores each blob under
its own `blobs/<prefix>/`, and onnxruntime 1.31 refuses external data whose
resolved path leaves the resolved model's directory.
"""

from pathlib import Path

from atrium.embed.materialized_model_file import materialized_model_file


def _symlinked_cache(root: Path) -> tuple[Path, Path]:
    snapshot = root / "snapshots/rev/onnx"
    snapshot.mkdir(parents=True)
    links = []
    for prefix, name in (("6a", "model.onnx"), ("2d", "model.onnx_data")):
        blob = root / "blobs" / prefix / "hash"
        blob.parent.mkdir(parents=True)
        blob.write_text(name)
        link = snapshot / name
        link.symlink_to(blob)
        links.append(link)
    return links[0], links[1]


def test_symlinked_files_end_up_in_the_same_real_directory(tmp_path):
    model, data = _symlinked_cache(tmp_path)
    assert model.resolve().parent != data.resolve().parent
    assert materialized_model_file(str(model)) == str(model)
    materialized_model_file(str(data))
    assert model.resolve().parent == data.resolve().parent
    assert (model.read_text(), data.read_text()) == ("model.onnx", "model.onnx_data")
    assert sorted(p.name for p in model.parent.iterdir()) == ["model.onnx", "model.onnx_data"]


def test_a_real_file_is_left_alone(tmp_path):
    real = tmp_path / "model.onnx"
    real.write_text("x")
    assert materialized_model_file(str(real)) == str(real)
    assert real.read_text() == "x"

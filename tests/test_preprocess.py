import numpy as np

from argos.analyzers import preprocess


def test_letterbox_preserves_aspect_and_pads_to_target():
    image = np.zeros((100, 50, 3), dtype=np.uint8)  # tall

    out, scale, (pad_x, pad_y) = preprocess.letterbox(image, (64, 64))

    assert out.shape == (64, 64, 3)
    assert scale == 64 / 100  # limited by the taller side
    assert pad_x > 0 and pad_y == 0


def test_to_nchw_float_shape_and_layout():
    image = np.full((8, 8, 3), 255, dtype=np.uint8)

    tensor = preprocess.to_nchw_float(image, normalize=False)

    assert tensor.shape == (1, 3, 8, 8)
    assert np.allclose(tensor, 1.0)


def test_l2_normalize_yields_unit_vector():
    vec = np.array([3.0, 4.0], dtype=np.float32)

    unit = preprocess.l2_normalize(vec)

    assert np.isclose(np.linalg.norm(unit), 1.0)


def test_cosine_similarity_orthogonal_and_identical():
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])

    assert preprocess.cosine_similarity(a, b) == 0.0
    assert np.isclose(preprocess.cosine_similarity(a, a), 1.0)

import numpy as np

from argos.analyzers.action import _build_stgcn_input, _softmax
from argos.config import Settings


def test_softmax_sums_to_one():
    probs = _softmax(np.array([2.0, 1.0, 0.1]))

    assert np.isclose(probs.sum(), 1.0)
    assert np.argmax(probs) == 0


def test_build_stgcn_input_shape_and_padding():
    # 5 frames of 17 keypoints (x, y, score); window 30 → left-padded.
    seq = [np.random.rand(17, 3).astype(np.float32) for _ in range(5)]

    tensor = _build_stgcn_input(seq, window=30)

    assert tensor.shape == (1, 3, 30, 17, 1)
    # First 25 frames are padding (all zero), last 5 carry data.
    assert np.all(tensor[0, :, :25, :, :] == 0)
    assert np.any(tensor[0, :, 25:, :, :] != 0)


def test_settings_rtsp_camera_map_parsing():
    settings = Settings(rtsp_cameras="front=rtsp://a/1;yard=rtsp://b/2;bad_pair")

    cameras = settings.rtsp_camera_map()

    assert cameras == {"front": "rtsp://a/1", "yard": "rtsp://b/2"}


def test_settings_cors_list():
    settings = Settings(cors_origins="http://a, http://b ,")

    assert settings.cors_origin_list() == ["http://a", "http://b"]

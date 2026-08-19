import numpy as np

from argos.detect.tracker import IouTracker, iou
from argos.detect.yolo import _as_anchors_first, _xywh_to_xyxy, decode


def test_iou_basic():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert 0.0 < iou((0, 0, 10, 10), (5, 5, 15, 15)) < 1.0


def test_tracker_keeps_id_across_frames():
    tracker = IouTracker(iou_threshold=0.3)

    first = tracker.update([(0, 0, 10, 20)])
    second = tracker.update([(1, 1, 11, 21)])  # overlapping → same id

    assert first[0][0] == second[0][0]


def test_tracker_new_id_for_disjoint_box():
    tracker = IouTracker(iou_threshold=0.3)

    a = tracker.update([(0, 0, 10, 10)])
    b = tracker.update([(100, 100, 110, 110)])  # no overlap → new id

    assert a[0][0] != b[0][0]


def test_as_anchors_first_transposes_channel_major():
    channel_major = np.zeros((1, 84, 8400), dtype=np.float32)

    out = _as_anchors_first(channel_major)

    assert out.shape == (8400, 84)


def test_xywh_to_xyxy():
    boxes = np.array([[50.0, 50.0, 20.0, 40.0]])  # center 50,50 ; w20 h40

    xyxy = _xywh_to_xyxy(boxes)

    assert xyxy.tolist() == [[40.0, 30.0, 60.0, 70.0]]


def test_decode_keeps_person_class_and_maps_box():
    # Ultralytics layout (1, 84, N); anchor 0 = person (class 0), box centered at 320,320 in 640.
    pred = np.zeros((1, 84, 100), dtype=np.float32)
    pred[0, :4, 0] = [320, 320, 100, 200]  # cx, cy, w, h
    pred[0, 4, 0] = 0.9                     # class 0 (person) score
    # No letterbox padding, scale 1 → frame is 640x640.
    boxes = decode(pred, scale=1.0, pad=(0, 0), frame_shape=(640, 640), conf_thres=0.3, iou_thres=0.5)

    assert len(boxes) == 1
    x1, y1, x2, y2, score = boxes[0]
    assert (x1, y1, x2, y2) == (270, 220, 370, 420)
    assert score > 0.8


def test_decode_drops_non_person_class():
    pred = np.zeros((1, 84, 100), dtype=np.float32)
    pred[0, :4, 0] = [320, 320, 100, 200]
    pred[0, 5, 0] = 0.9  # class 1 (not person)

    boxes = decode(pred, scale=1.0, pad=(0, 0), frame_shape=(640, 640), conf_thres=0.3, iou_thres=0.5)

    assert boxes == []

from argos.zones import Zone, ZoneStore, foot_point_normalized, point_in_polygon

SQUARE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def test_point_in_polygon_inside_and_outside():
    assert point_in_polygon((0.5, 0.5), SQUARE) is True
    assert point_in_polygon((1.5, 0.5), SQUARE) is False
    assert point_in_polygon((-0.1, 0.5), SQUARE) is False


def test_point_in_polygon_degenerate():
    assert point_in_polygon((0.5, 0.5), [(0.0, 0.0), (1.0, 1.0)]) is False  # <3 points


def test_foot_point_is_bottom_center_normalized():
    # box centered x, bottom at frame height → (0.5, 1.0)
    assert foot_point_normalized((100, 100, 300, 500), (400, 500)) == (0.5, 1.0)


def test_zone_contains_uses_its_polygon():
    zone = Zone(camera="front", name="driveway", points=SQUARE)

    assert zone.contains((0.5, 0.5)) is True
    assert zone.contains((2.0, 2.0)) is False


def test_zone_store_add_list_remove(tmp_path):
    store = ZoneStore(tmp_path / "zones.json")
    z = store.add(Zone(camera="front", name="gate", points=SQUARE, kind="alert"))

    assert [zz.name for zz in store.for_camera("front")] == ["gate"]
    assert store.for_camera("yard") == []
    assert store.remove(z.id) is True
    assert store.for_camera("front") == []
    assert store.remove("missing") is False

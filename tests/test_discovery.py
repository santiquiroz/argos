from argos.discovery.defaults import DEFAULT_CREDENTIALS
from argos.discovery.hikvision import parse_channel_count, parse_device_info
from argos.discovery.models import Credential, DiscoveredCamera, rtsp_url
from argos.discovery.onvif import parse_xaddr_ips


def test_rtsp_url_substream_and_mainstream():
    assert rtsp_url("10.0.0.5", 2, substream=True) == "rtsp://10.0.0.5:554/Streaming/Channels/202"
    assert rtsp_url("10.0.0.5", 1, substream=False) == "rtsp://10.0.0.5:554/Streaming/Channels/101"


def test_rtsp_url_embeds_credentials():
    cred = Credential("admin", "12345")

    url = rtsp_url("10.0.0.5", 1, credential=cred)

    assert url == "rtsp://admin:12345@10.0.0.5:554/Streaming/Channels/102"


def test_discovered_camera_builds_url_per_channel():
    cam = DiscoveredCamera(ip="10.0.0.9", channels=3, default_credential=Credential("admin", "x"))

    urls = cam.rtsp_urls(substream=True)

    assert len(urls) == 3
    assert urls[2] == "rtsp://admin:x@10.0.0.9:554/Streaming/Channels/302"
    assert cam.insecure is True


def test_credential_masking_hides_password():
    assert Credential("admin", "12345").masked() == "admin:*****"
    assert Credential("admin", "").masked() == "admin:(blank)"


def test_parse_xaddr_ips_extracts_device_addresses():
    payload = (
        "<d:ProbeMatch><d:XAddrs>http://192.168.1.64/onvif/device_service "
        "http://10.0.0.2:8000/onvif/device_service</d:XAddrs></d:ProbeMatch>"
    )

    ips = parse_xaddr_ips(payload)

    assert ips == {"192.168.1.64", "10.0.0.2"}


def test_parse_device_info_namespace_agnostic():
    xml = "<DeviceInfo><model>DS-7608</model><deviceName>HiLook DVR</deviceName><serialNumber>ABC</serialNumber></DeviceInfo>"

    info = parse_device_info(xml)

    assert info["model"] == "DS-7608"
    assert info["name"] == "HiLook DVR"


def test_parse_channel_count():
    xml = "<list><VideoInputChannel/><VideoInputChannel/><VideoInputChannel/></list>"

    assert parse_channel_count(xml) == 3
    assert parse_channel_count("<empty/>") == 1  # floor of 1


def test_default_credentials_are_credentials():
    assert len(DEFAULT_CREDENTIALS) >= 3
    assert all(isinstance(c, Credential) for c in DEFAULT_CREDENTIALS)

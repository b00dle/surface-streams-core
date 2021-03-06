"""
This script contains constant protocol based gstreamer caps to establish video stream receiving.
"""

JPEG_CAPS_ALT = "application/x-rtp, " \
            "media=(string)application, " \
            "clock-rate=(int)90000, " \
            "encoding-name=(string)X-GST, " \
            "caps=(string)aW1hZ2UvanBlZywgc29mLW1hcmtlcj0oaW50KTAsIHdpZHRoPShpbnQpMTI4MCwgaGVpZ2h0PShpbnQpNzIwLCBwaXhlbC1hc3BlY3QtcmF0aW89KGZyYWN0aW9uKTEvMSwgZnJhbWVyYXRlPShmcmFjdGlvbikyNDAwMC8xMDAx, " \
            "capsversion=(string)0, " \
            "payload=(int)96, " \
            "ssrc=(uint)2277765570, " \
            "timestamp-offset=(uint)3095164038, " \
            "seqnum-offset=(uint)16152"

VP8_CAPS_ALT = "application/x-rtp, " \
           "media=(string)video, " \
           "clock-rate=(int)90000, " \
           "encoding-name=(string)VP8-DRAFT-IETF-01, " \
           "payload=(int)96, " \
           "ssrc=(uint)2990747501, " \
           "clock-base=(uint)275641083, " \
           "seqnum-base=(uint)34810"

VP9_CAPS_ALT = "application/x-rtp, " \
           "media=video, " \
           "clock-rate=90000, " \
           "encoding-name=VP9, " \
           "payload=96, " \
           "ssrc=2628574034, " \
           "timestamp-offset=3124680929, " \
           "seqnum-offset=7023, " \
           "a-framerate=23.976023976023978"

MP4_CAPS_ALT = "application/x-rtp, " \
           "media=(string)video, " \
           "clock-rate=(int)90000, " \
           "encoding-name=(string)MP4V-ES, " \
           "profile-level-id=(string)1, " \
           "config=(string)000001b001000001b58913000001000000012000c48d8800cd3204709443000001b24c61766335362e312e30, " \
           "payload=(int)96, " \
           "ssrc=(uint)2873740600, " \
           "timestamp-offset=(uint)391825150, " \
           "seqnum-offset=(uint)2980"


H264_CAPS_ALT = "application/x-rtp, " \
            "media=video, " \
            "clock-rate=90000, " \
            "encoding-name=H264, " \
            "packetization-mode=1, " \
            "profile-level-id=f40032, " \
            "payload=96, " \
            "ssrc=1577364544, " \
            "timestamp-offset=1721384841, " \
            "seqnum-offset=7366, " \
            "a-framerate=25"

H265_CAPS_ALT = "application/x-rtp, " \
            "media=video, " \
            "payload=96, " \
            "clock-rate=90000, " \
            "encoding-name=H265, " \
            "ssrc=2828246746, " \
            "timestamp-offset=1863230164, " \
            "seqnum-offset=12204, " \
            "a-framerate=23.976023976023978"

DEFAULT_CAPS = "application/x-rtp, media=video, clock-rate=90000, payload=96"
H264_CAPS = DEFAULT_CAPS + ", encoding-name=H264"
H265_CAPS = DEFAULT_CAPS + ", encoding-name=H265"
VP8_CAPS = DEFAULT_CAPS + ", encoding-name=VP8"
VP9_CAPS = DEFAULT_CAPS + ", encoding-name=VP9"
MP4_CAPS = DEFAULT_CAPS + ", encoding-name=MP4V-ES, a-framerate=10, profile-level-id=1, " \
          "config=000001b001000001b58913000001000000012000c48d88005514042d1443000001b24c61766335362e36302e313030"
JPEG_CAPS = JPEG_CAPS_ALT #"application/x-rtp, media=application, clock-rate=90000, payload=96, encoding-name=X-GST"

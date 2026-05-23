# Go2 多媒体接口 → A2 兼容性参考

> 来源: 宇树官方文档 | Go2 多媒体服务接口 | 2025-11-21

## JPEG 拍照（A2 可用 ✅）

`VideoClient.GetImageSample()` → RPC 接口，返回 JPEG 字节

```cpp
#include <unitree/robot/go2/video/video_client.hpp>
video_client.GetImageSample(image_sample);  // → vector<uint8_t>
```

宇树官方确认：A2 可直接使用 Go2 的 VideoClient 接口。

## h264 图传（A2 可用 ✅）

UDP multicast: `230.1.1.1:1720`，GStreamer pipeline

```bash
gst-launch-1.0 udpsrc address=230.1.1.1 port=1720 multicast-iface=eth0 \
  ! application/x-rtp, media=video, encoding-name=H264 \
  ! rtph264depay ! h264parse ! avdec_h264 \
  ! videoconvert ! autovideosink
```

**参数:**
- 帧率: 15Hz
- 分辨率: 1280×720
- 水平 FOV: 100°
- 垂直 FOV: 56°
- 不推荐 DDS 图传（只传 h264 编码后数据，仍需解码）

OpenCV 拉流（Python）：
```python
import cv2
gst_str = "udpsrc address=230.1.1.1 port=1720 multicast-iface=eth0 " \
          "! application/x-rtp, media=video, encoding-name=H264 " \
          "! rtph264depay ! h264parse ! avdec_h264 " \
          "! videoconvert ! video/x-raw,width=1280,height=720,format=BGR " \
          "! appsink drop=1"
cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
```

依赖: `sudo apt install libgstreamer1.0-dev gstreamer1.0-plugins-*`

## 麦克风 + 喇叭（A2 自有 DDS 接口）

A2 内嵌扬声器 + 麦克风阵列，通过 DDS 接口控制：
- `include/unitree/robot/a2/audio/`

## 兼容性速查

| 功能 | Go2 方式 | A2 可用？ |
|---|---|---|
| JPEG 拍照 | `VideoClient.GetImageSample()` RPC | ✅ |
| h264 图传 | UDP `230.1.1.1:1720` + Gst | ✅ |
| 麦克风 | DDS (`a2/audio/`) | ✅ A2 自有 |
| 喇叭 | DDS (`a2/audio/`) | ✅ A2 自有 |

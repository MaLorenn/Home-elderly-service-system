import cv2

def list_camera_devices(max_devices=10):
    available_devices = []
    for device in range(max_devices):
        cap = cv2.VideoCapture(device)
        if cap.isOpened():
            available_devices.append(device)
            cap.release()
    return available_devices

if __name__ == "__main__":
    devices = list_camera_devices()
    if devices:
        print("可用的摄像头设备号:", devices)
    else:
        print("没有找到可用的摄像头设备")
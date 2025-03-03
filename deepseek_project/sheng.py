import pyaudio

def list_microphones():
    p = pyaudio.PyAudio()
    microphones = []
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info.get('maxInputChannels', 0) > 0:  # 检查是否为输入设备
            microphones.append({
                "index": device_info["index"],
                "name": device_info["name"],
                "channels": device_info["maxInputChannels"],
                "default_sample_rate": device_info.get("defaultSampleRate", "N/A")
            })
    p.terminate()  # 释放资源
    return microphones

if __name__ == "__main__":
    mics = list_microphones()
    if not mics:
        print("未找到可用的麦克风。")
    else:
        print("可用的麦克风设备列表：")
        for mic in mics:
            print(f"Index: {mic['index']}, 名称: {mic['name']}, 通道数: {mic['channels']}, 默认采样率: {mic['default_sample_rate']}")

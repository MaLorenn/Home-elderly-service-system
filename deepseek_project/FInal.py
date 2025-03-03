"""
DeepSeek全语音交互助手（增强版）
整合功能：
1. 语音唤醒与输入
2. AI大模型智能响应
3. 网络信息增强
4. 语音回复输出
5. 对话日志记录
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from aip import AipSpeech
import speech_recognition as sr
from playsound import playsound
import dashscope
from dashscope.audio.tts_v2 import *
from pydub import AudioSegment
from pydub.playback import play

# 加载环境变量
load_dotenv()

# -------------------
# 硬件配置区（按需修改）
# -------------------
MIC_INDEX = 15  # 麦克风设备索引
WAKE_WORD = "小马"  # 唤醒词

# -------------------
# API配置区
# -------------------
# DeepSeek配置
DEEPSEEK_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 百度语音识别配置
SST_APP_ID = os.getenv("SST_APP_ID")
SST_API_KEY = os.getenv("SST_API_KEY")
SST_SECRET_KEY = os.getenv("SST_SECRET_KEY")

# 阿里云语音合成配置
TTS_API_KEY = os.getenv("TTS_API_KEY")

# 全局配置
SAVE_FILE_PATH = "conversation.txt"
SEARCH_TRIGGERS = ["最新", "今年", "新闻", "天气", "实时", "现在", "2025"]

# -------------------
# 初始化API客户端
# -------------------
sst_client = AipSpeech(SST_APP_ID, SST_API_KEY, SST_SECRET_KEY)
dashscope.api_key = TTS_API_KEY

# -------------------
# 核心功能类
# -------------------
class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone(device_index=MIC_INDEX)
        self._configure_audio()
        
        self.deepseek_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        self.search_headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }

    def _configure_audio(self):
        """音频设备初始化"""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            self.recognizer.energy_threshold = self.recognizer.energy_threshold * 2.0
            self.recognizer.pause_threshold = 3.0

    def _synthesize_speech(self, text: str):
        """文字转语音并播放"""
        try:
            synthesizer = SpeechSynthesizer(model="cosyvoice-v1", voice="longwan")
            audio_data = synthesizer.call(text)

            with open('response.mp3', 'wb') as f:
                f.write(audio_data)

            # 使用 pydub 播放音频
            audio = AudioSegment.from_mp3('response.mp3')
            play(audio)
        except Exception as e:
            print(f"语音合成失败：{str(e)}")

    def voice_to_text(self, audio_data: bytes) -> str:
        """执行语音识别"""
        try:
            result = sst_client.asr(audio_data, 'wav', 16000, {'dev_pid': 1537})
            if result['err_no'] == 0:
                return result['result'][0].strip()
            print(f"识别错误 {result['err_no']}: {result.get('err_msg', '')}")
        except Exception as e:
            print(f"识别异常：{str(e)}")
        return ""

    def _deepseek_response(self, question: str) -> str:
        """与DeepSeek交互获取响应"""
        messages = self._build_messages(question)
        
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=self.deepseek_headers,
                json={
                    "model": "deepseek-ai/DeepSeek-V3",
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"请求失败：{str(e)}"

    def _web_search(self, query: str) -> str:
        """执行谷歌搜索并返回精炼结果"""
        try:
            response = requests.post(
                url="https://google.serper.dev/search",
                headers=self.search_headers,
                json={"q": query, "gl": "cn"},
                timeout=15
            )
            response.raise_for_status()
            
            # 解析并组合搜索结果
            results = response.json().get("organic", [])[:3]  # 取前三条
            return "\n".join(
                [f"• {res.get('title', '')}：{res.get('snippet', '')}" 
                 for res in results if res.get("snippet")]
            ) or "未找到相关实时信息"
            
        except Exception as e:
            print(f"\n⚠️ 搜索失败：{str(e)}")
            return ""

    def _need_search(self, question: str) -> bool:
        """判断是否需要联网搜索"""
        return any(keyword in question for keyword in SEARCH_TRIGGERS)

    def _build_messages(self, question: str) -> list:
        """动态构建对话上下文"""
        base_context = f"""你是一名能够结合实时信息进行回答的智能虚拟陪伴助手，语气活泼，回复内容请以人正常说话的方式，
当提到孤独时，回复不超过2句话，并以开放性问题结尾。当前日期是{datetime.now().strftime('%Y-%m-%d')}。"""
        messages = [{"role": "system", "content": base_context}]

        if self._need_search(question):
            search_result = self._web_search(question)
            if search_result:
                messages.append({
                    "role": "assistant",
                    "content": f"【网络信息监测】\n{search_result}\n请结合以上信息进行回答："
                })

        messages.append({"role": "user", "content": question})
        return messages


    def _wakeup_detection(self) -> bool:
        """持续监听直到检测到唤醒词"""
        print(f"\n等待唤醒词『{WAKE_WORD}』...")
        with self.mic as source:
            while True:
                try:
                    # 每次监听1秒音频片段
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=1)
                    wav_data = audio.get_wav_data(convert_rate=16000)
                    
                    # 执行唤醒词识别
                    result = sst_client.asr(wav_data, 'wav', 16000, {'dev_pid': 1537})
                    if result.get('err_no') == 0:
                        text = result['result'][0].strip()
                        print(f"唤醒检测文本: {text}")
                        if WAKE_WORD in text:
                            self._synthesize_speech("我在")  # 语音反馈
                            return True
                            
                except sr.WaitTimeoutError:
                    continue  # 静默时段继续循环
                except Exception as e:
                    print(f"唤醒检测异常: {str(e)}")
                    continue

    def _record_audio(self) -> bytes:
        """执行主要录音流程"""
        print("\n请开始说话（静默2秒自动结束）...")
        with self.mic as source:
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=5,           # 最长静默等待时间
                    phrase_time_limit=10  # 单次说话最长时长
                )
                print(">> 录音结束，开始处理...")
                return audio.get_wav_data(convert_rate=16000)
            except sr.WaitTimeoutError:
                print(">> 未检测到语音输入")
                return b''
            except Exception as e:
                print(f">> 录音失败: {str(e)}")
                return b''

    def _log_entry(self, file_handler, content: str, is_question: bool = False):
        """统一日志记录方法"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = "用户提问" if is_question else "AI回复"
        log_entry = f"\n[{timestamp}] {prefix}：\n{content}\n"
        
        # 同时写入文件和打印输出
        file_handler.write(log_entry)
        file_handler.flush()
        print(log_entry)

    def process_conversation(self):
        """完整交互流程"""
        with open(SAVE_FILE_PATH, "a", encoding="utf-8") as log:
            print("\n系统就绪...")
            while True:
                try:
                    # 唤醒检测
                    if self._wakeup_detection():
                        # 主录音流程
                        audio_data = self._record_audio()
                        if not audio_data:
                            continue
                            
                        # 语音转文字
                        question = self.voice_to_text(audio_data)
                        if not question:
                            continue
                            
                        # 记录并处理
                        self._log_entry(log, question, True)
                        response = self._deepseek_response(question)
                        self._log_entry(log, response)
                        
                        # 语音反馈
                        print(f"\nAI回复：{response}")
                        self._synthesize_speech(response)
                        
                except KeyboardInterrupt:
                    print("\n服务终止")
                    break

    # 以下保留原唤醒检测和录音方法（实现略）
    
if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.process_conversation()

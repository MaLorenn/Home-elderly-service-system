import cv2
from flask import Flask, Response, render_template_string, request

app = Flask(__name__)
cap = None
camera_lock = False


def generate_frames():
    global cap, camera_lock
    try:
        camera_lock = True
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("无法打开摄像头")
            return
        while True:
            success, frame = cap.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except Exception as e:
        print(f"发生异常: {e}")


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/release_camera', methods=['POST'])
def release_camera():
    global cap, camera_lock
    if camera_lock and cap is not None:
        cap.release()
        camera_lock = False
        print("摄像头资源已释放")
    return 'OK'


@app.route('/')
def index():
    html = """
    <html>
      <head>
        <style>
          body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 50px;
          }
          h1 {
            font-size: 36px;
            margin-bottom: 20px;
          }
          button {
            padding: 10px 20px;
            font-size: 18px;
            cursor: pointer;
          }
        </style>
        <script>
          window.addEventListener('beforeunload', function() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/release_camera', false);
            xhr.send();
          });
        </script>
      </head>
      <body>
        <h1>老人伴侣实时监控平台</h1>
        <button id="show-video-button" onclick="window.location.href='/video_page'">监控画面</button>
      </body>
    </html>
    """
    return render_template_string(html)


@app.route('/video_page')
def video_page():
    html = """
    <html>
      <head>
        <style>
          body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 50px;
          }
          button {
            padding: 10px 20px;
            font-size: 18px;
            cursor: pointer;
            margin-bottom: 20px;
          }
        </style>
        <script>
          window.addEventListener('beforeunload', function() {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/release_camera', false);
            xhr.send();
          });
        </script>
      </head>
      <body>
        <button onclick="window.location.href='/'">返回首页</button>
        <img src="/video_feed" width="640">
      </body>
    </html>
    """
    return render_template_string(html)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
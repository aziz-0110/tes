from flask import Flask, Response
from picamera2 import Picamera2, Preview
import cv2
import time

app = Flask(__name__)
camera = Picamera2()

@app.route('/video_feed')
def video_feed():
    # Mengatur konfigurasi video
    camera.configure(camera.create_video_configuration())
    camera.start()
    
    # Menghasilkan stream video
    return Response(stream_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

def stream_video():
    while True:
        # Ambil frame dari kamera
        frame = camera.capture_array()
        # Encode frame ke JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return '''
    <html>
    <head>
        <title>Raspberry Pi Camera Stream</title>
    </head>
    <body>
        <h1>Raspberry Pi Camera Stream</h1>
        <img src="/video_feed" width="640" height="480">
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

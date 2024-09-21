from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)
camera = Picamera2()

@app.route('/video_feed')
def video_feed():
    return Response(camera.start_recording("output.h264", format="h264"), mimetype='video/h264')

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
    camera.configure(camera.create_video_configuration())
    camera.start()
    app.run(host='0.0.0.0', port=5000)

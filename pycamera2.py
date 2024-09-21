import io
import time
import logging
import socketserver
from http import server
from threading import Condition, Thread
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

PAGE = """\
<html>
<head>
<title>Raspberry Pi - Surveillance Camera</title>
</head>
<body>
<center><h1>Raspberry Pi - Surveillance Camera</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingOutput(io.BytesIO):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # Frame baru, copy buffer yang ada dan notify semua clients bahwa frame tersedia
            self.seek(0)
            self.frame = self.read()
            with self.condition:
                self.condition.notify_all()
            self.seek(0)
            self.truncate()
        return super().write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def start_streaming_server():
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()

# Inisialisasi Picamera2
picam2 = Picamera2()
camera_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(camera_config)

# Membuat encoder MJPEG dan output ke StreamingOutput
output = StreamingOutput()
encoder = MJPEGEncoder()

# Mulai merekam
picam2.start_recording(encoder, FileOutput(output))

try:
    # Mulai server streaming di thread terpisah
    server_thread = Thread(target=start_streaming_server)
    server_thread.daemon = True
    server_thread.start()

    # Menjalankan streaming selama 10 menit atau sesuai kebutuhan
    while True:
        time.sleep(1)

finally:
    picam2.stop_recording()
    picam2.close()

import io
from picamera2 import Picamera2, Preview
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import logging
import socketserver
from threading import Condition
from http import server

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
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
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

# Inisialisasi Picamera2
picam2 = Picamera2()
camera_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(camera_config)

# Menggunakan io.BytesIO sebagai output
buffer = io.BytesIO()
output = StreamingOutput()

# Setup Encoder dan Output
encoder = MJPEGEncoder()
# Menuliskan hasil encoding ke buffer
picam2.start_recording(encoder, FileOutput(buffer))

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    
    # Baca dari buffer dan tulis ke StreamingOutput di thread terpisah
    def buffer_to_output():
        while True:
            buffer.seek(0)
            data = buffer.read()
            if data:
                output.write(data)
            buffer.seek(0)
            buffer.truncate()
    
    import threading
    threading.Thread(target=buffer_to_output, daemon=True).start()
    
    # Mulai server streaming
    server.serve_forever()
finally:
    picam2.stop_recording()
    picam2.close()

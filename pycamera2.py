from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import time
import threading


# Membuat instance Flask
app = Flask(__name__)

# Membuat instance kamera
camera = Picamera2()

# Variabel untuk menyimpan frame kamera
frame = None

# Flag untuk menjalankan loop kamera
camera_running = False

# Fungsi untuk mengambil frame dari kamera
def camera_thread():
    global frame, camera_running
    # Konfigurasi kamera
    config = camera.create_video_configuration(
        main={"size": (1640, 1230), "format": "RGB888"},
        controls={"FrameDurationLimits": (33333, 33333)},  # 30 fps
    )
    camera.configure(config)
    camera.start()
    camera_running = True

    while camera_running:
        frame = camera.capture_array()
        time.sleep(0.03)  # 30 fps

    camera.stop()

# Rute untuk streaming video langsung di '/'
@app.route('/')
def video_feed():
    return Response(stream_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Fungsi generator untuk streaming video
def stream_video():
    global frame
    while True:
        if frame is not None:
            # Encode frame ke JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_jpg = buffer.tobytes()

            # Mengirim frame dengan boundary
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_jpg + b'\r\n')
        else:
            time.sleep(0.1)  # Tunggu jika frame belum tersedia

# Menjalankan kamera pada thread terpisah
camera_thread_instance = threading.Thread(target=camera_thread)
camera_thread_instance.start()

# Menjalankan server Flask
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        # Menghentikan loop kamera saat aplikasi berhenti
        camera_running = False
        camera_thread_instance.join()

#!/usr/bin/env python3

import io
from threading import Condition
from flask import Flask, render_template, Response
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (1296, 972)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


def stream_generator():
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
            yield (b'--FRAME\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'b'\r\n' + frame + b'\r\n')


@app.route('/stream.mjpg')
def stream():
    headers = {
        'Age': '0',
        'Cache-Control': 'no-cache, private',
        'Pragma': 'no-cache',
    }

    return Response(stream_generator(), mimetype='multipart/x-mixed-replace; boundary=FRAME', headers=headers)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000, threaded=True)
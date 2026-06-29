import roslibpy
import cv2
import numpy as np
import json
import base64
import time
import sys
import threading


class Ros2Connection:
    def __init__(self, host='localhost', port=9090, cam_index=0, fps=10):
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()

        self.pub = roslibpy.Topic(
            self.client,
            'openduck/head_cam/compressed',
            'sensor_msgs/CompressedImage'
        )
        self.pub.advertise()

        self.sub = roslibpy.Topic(
            self.client,
            'openduck/commands',
            'std_msgs/String'
        )
        self.sub.subscribe(self.command_callback)

        self.cap = cv2.VideoCapture(cam_index)

        # カメラ内部バッファを小さくする。効かない環境もあるが入れておく価値あり。
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self.interval = 1.0 / fps
        self.count = 0

        self.commands = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # 追加: 最後に送信した時刻
        self.last_publish_time = 0.0

        # 追加: 送信中フラグ代わりのロック
        self.publish_lock = threading.Lock()

        print('Ros2Connection started with roslibpy')

    # コマンドの受取
    def command_callback(self, message):
        print(f"Received command message: {message}")
        try:
            data = message.get('data', '')
            try:
                self.commands = json.loads(data)
            except json.JSONDecodeError:
                self.commands = [float(x) for x in data.split(',')]

            print(f'commands received: {self.commands}')

        except Exception as e:
            print(f'Error in command_callback: {e}')

    # 画像の送信。呼ばれても、条件を満たさない場合は送らずreturnする。
    def publish_image(self, frame):
        now = time.monotonic()

        # 送信周期に達していなければ捨てる
        if now - self.last_publish_time < self.interval:
            return False

        # もし前回の publish_image がまだ処理中なら捨てる
        if not self.publish_lock.acquire(blocking=False):
            return False

        try:
            # ここで時刻を更新しておく
            # これにより、エンコード中やpublish中に次が来ても間引ける
            self.last_publish_time = now

            # 必要なら解像度を下げる
            # frame = cv2.resize(frame, (640, 480))

            # JPEG圧縮
            ok, buf = cv2.imencode(
                '.jpg',
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )

            if not ok:
                print('Failed to encode frame')
                return False

            # rosbridge 経由では uint8[] を base64 文字列で送る
            encoded_data = base64.b64encode(buf.tobytes()).decode('ascii')

            msg = roslibpy.Message({
                'format': 'jpeg',
                'data': encoded_data
            })

            self.pub.publish(msg)

            return True

        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            self.cleanup()
            sys.exit(0)

        except Exception as e:
            print(f'Error in publish_image: {e}')
            return False

        finally:
            self.publish_lock.release()

    def subscribe_commands(self):
        return self.commands

    def cleanup(self):
        try:
            if self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass

        try:
            self.sub.unsubscribe()
        except Exception:
            pass

        try:
            self.pub.unadvertise()
        except Exception:
            pass

        try:
            self.client.terminate()
        except Exception:
            pass
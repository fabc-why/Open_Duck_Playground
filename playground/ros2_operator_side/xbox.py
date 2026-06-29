import roslibpy
import numpy as np
import cv2
import json
import base64
import argparse
import time
import pygame


class OperationSide:
    def __init__(self, host='localhost', port=9090):
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()

        self.sub = roslibpy.Topic(
            self.client,
            'openduck/head_cam/compressed',
            'sensor_msgs/CompressedImage'
        )
        self.sub.subscribe(self.listener_callback)

        self.pub = roslibpy.Topic(
            self.client,
            'openduck/commands',
            'std_msgs/String'
        )
        self.pub.advertise()

        self.running = True
        self.command = [0.0] * 7

        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError('Xbox controller が見つかりません')

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()

        print('OperationSide started')
        print(f'Controller: {self.joystick.get_name()}')
        print(f'axes: {self.joystick.get_numaxes()}')
        print('axis 1: forward/backward')
        print('axis 0: left/right')
        print('axis 3: yaw')
        print('Ctrl+C to quit')

    def deadzone(self, value, threshold=0.15):
        if abs(value) < threshold:
            return 0.0
        return value

    def publish_controller_command(self):
        pygame.event.pump()

        axis_0_raw = self.joystick.get_axis(0)
        axis_1_raw = self.joystick.get_axis(1)
        axis_3_raw = self.joystick.get_axis(2)

        axis_0 = self.deadzone(axis_0_raw)
        axis_1 = self.deadzone(axis_1_raw)
        axis_3 = self.deadzone(axis_3_raw)

        max_forward = 0.2
        max_side = 0.2
        max_yaw = 1.0

        forward = -axis_1 * max_forward
        side = -axis_0 * max_side
        yaw = -axis_3 * max_yaw

        self.command = [
            forward,
            side,
            yaw,
            0.0,
            0.0,
            0.0,
            0.0
        ]

        msg = roslibpy.Message({
            'data': json.dumps(self.command)
        })

        self.pub.publish(msg)

        print(
            f'raw: '
            f'a0={axis_0_raw:.3f}, '
            f'a1={axis_1_raw:.3f}, '
            f'a3={axis_3_raw:.3f} | '
            f'cmd: '
            f'forward={forward:.3f}, '
            f'side={side:.3f}, '
            f'yaw={yaw:.3f}'
        )

    def listener_callback(self, message):
        try:
            data = message.get('data', None)

            if data is None:
                print('Image message has no data')
                return

            if isinstance(data, str):
                image_bytes = base64.b64decode(data)
                arr = np.frombuffer(image_bytes, dtype=np.uint8)

            elif isinstance(data, list):
                arr = np.array(data, dtype=np.uint8)

            else:
                print(f'Unsupported image data type: {type(data)}')
                return

            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if frame is None:
                print('Failed to decode image')
                return

            cv2.imshow('operation_side', frame)
            cv2.waitKey(1)

        except Exception as e:
            print(f'Error decoding/displaying image: {e}')

    def loop(self):
        rate = 20.0
        dt = 1.0 / rate

        try:
            while self.running and self.client.is_connected:
                self.publish_controller_command()
                time.sleep(dt)

        except KeyboardInterrupt:
            print('KeyboardInterrupt')

        finally:
            self.cleanup()

    def cleanup(self):
        self.running = False

        try:
            stop_msg = roslibpy.Message({
                'data': json.dumps([0.0] * 7)
            })
            self.pub.publish(stop_msg)
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
            cv2.destroyAllWindows()
        except Exception:
            pass

        try:
            pygame.quit()
        except Exception:
            pass

        try:
            self.client.terminate()
        except Exception:
            pass

        print('OperationSide shutdown complete')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='172.17.156.126')
    parser.add_argument('--port', type=int, default=9090)
    args = parser.parse_args()

    node = OperationSide(
        host=args.host,
        port=args.port
    )
    node.loop()


if __name__ == '__main__':
    main()

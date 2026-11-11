import queue
import numpy as np
import pygame

from core import mac_dinh


def spawn_camera(world, bp_library, ego_car, view_idx):
    bp = bp_library.find('sensor.camera.rgb')
    bp.set_attribute('image_size_x', str(mac_dinh.CAMERA_W))
    bp.set_attribute('image_size_y', str(mac_dinh.CAMERA_H))
    bp.set_attribute('fov', str(mac_dinh.CAMERA_FOV))
    cam = world.spawn_actor(bp, mac_dinh.CAMERA_VIEWS[view_idx][1], attach_to=ego_car)
    q = queue.Queue()
    cam.listen(q.put)
    return cam, q


def image_to_surface(image):
    # Ảnh CARLA là BGRA, pygame cần RGB và trục (rộng, cao)
    arr = np.frombuffer(image.raw_data, dtype=np.uint8)
    arr = arr.reshape((image.height, image.width, 4))[:, :, :3][:, :, ::-1]
    return pygame.surfarray.make_surface(arr.swapaxes(0, 1))


def manual_control(keys, control):
    # W ga, S phanh, Q số lùi, SPACE phanh tay, A/D đánh lái (giới hạn ±0.7), thả phím thì lái về giữa
    control.throttle = 1.0 if keys[pygame.K_w] else 0.0
    control.brake = 1.0 if keys[pygame.K_s] else 0.0
    control.hand_brake = bool(keys[pygame.K_SPACE])
    control.reverse = bool(keys[pygame.K_q])   # giữ Q là số lùi, rồi W để lùi
    if keys[pygame.K_a]:
        control.steer = max(-0.7, control.steer - 0.05) if control.steer <= 0 else 0.0
    elif keys[pygame.K_d]:
        control.steer = min(0.7, control.steer + 0.05) if control.steer >= 0 else 0.0
    else:
        control.steer = 0.0

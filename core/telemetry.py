import math

import carla


def read_telemetry(ego_car, control, step, dt):
    """Đọc trạng thái xe Ego tại 1 step, trả về dict đã làm tròn."""
    transform = ego_car.get_transform()
    velocity = ego_car.get_velocity()
    accel = ego_car.get_acceleration()

    x, y = transform.location.x, transform.location.y
    pitch, yaw, roll = transform.rotation.pitch, transform.rotation.yaw, transform.rotation.roll

    # Chuyển đổi góc Yaw từ độ sang Radian
    yaw_rad = math.radians(yaw)
    cos_y = math.cos(yaw_rad)
    sin_y = math.sin(yaw_rad)

    # 1. Chiếu Vận tốc từ World Frame sang Local Body Frame
    vx_world, vy_world = velocity.x, velocity.y
    vx =  vx_world * cos_y + vy_world * sin_y    # Vận tốc dọc thân xe (Longitudinal)
    vy = -vx_world * sin_y + vy_world * cos_y    # Vận tốc ngang thân xe (Lateral / Slip)
    v = math.sqrt(vx_world**2 + vy_world**2)     # Tổng vận tốc trong mặt phẳng

    # 2. Chiếu Gia tốc từ World Frame sang Local Body Frame
    ax_world, ay_world = accel.x, accel.y
    ax =  ax_world * cos_y + ay_world * sin_y    # Gia tốc dọc (Tăng tốc / Phanh)
    ay = -ax_world * sin_y + ay_world * cos_y    # Gia tốc ngang (Lực ly tâm ôm cua)

    return {
        'time': round(step * dt, 3), 'time_step': step,
        'x': round(x, 4), 'y': round(y, 4), 'v': round(v, 4),
        'vx': round(vx, 4), 'vy': round(vy, 4),
        'ax': round(ax, 4), 'ay': round(ay, 4),
        'pitch': round(pitch, 4), 'yaw': round(yaw, 4), 'roll': round(roll, 4),
        'steer': round(control.steer, 4),
        # Góc bánh trước trái thật (độ), CARLA đọc thẳng từ mô hình vật lý
        'steer_deg': round(ego_car.get_wheel_steer_angle(carla.VehicleWheelLocation.FL_Wheel), 3),
        'throttle': round(control.throttle, 4),
        'brake': round(control.brake, 4),
    }

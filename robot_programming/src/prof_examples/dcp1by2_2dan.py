
from neuromeka import IndyDCP3
import time

indy = IndyDCP3("192.168.3.2")

PICK_BASE = [0.29046894861336457, 0.37377, 0.410567591089456]
PLACE_BASE = [0.1548543564286797, 0.32610252214202605, 0.41056767700108]

GRID_X = 1
GRID_Y = 2
NUM_LAYERS = 2
LAYER_HEIGHT = 0.03
OFFSET_X = 0.04
OFFSET_Y = 0.04
RETRACT_Z = 0.05

ROTATION = [-175.85, 5.51, 169.58]
ROTATION1 = [1.96, -177.90, 3.90]


def move_done_check():
    while True:
        status = indy.get_robot_status()

        if status["movedone"]:
            break

        time.sleep(0.2)


def generate_grid(base, grid_x, grid_y,
                  offset_x, offset_y,
                  num_layers, layer_height):

    coords = []

    for layer in range(num_layers):

        z = base[2] + layer * layer_height

        for i in range(grid_y):

            for j in range(grid_x):

                x = base[0] + j * offset_x
                y = base[1] + i * offset_y

                coords.append([x, y, z])

    return coords


def execute_pick_and_place():

    indy.move_home()
    move_done_check()

    place_positions = generate_grid(
        PLACE_BASE,
        GRID_X,
        GRID_Y,
        OFFSET_X,
        OFFSET_Y,
        NUM_LAYERS,
        LAYER_HEIGHT
    )

    indy.move_task_abs([
        PICK_BASE[0],
        PICK_BASE[1],
        PICK_BASE[2] + RETRACT_Z,
        *ROTATION
    ])

    move_done_check()

    for place in place_positions:

        indy.move_task_abs([
            PICK_BASE[0],
            PICK_BASE[1],
            PICK_BASE[2] + RETRACT_Z,
            *ROTATION
        ])

        move_done_check()

        indy.move_task_abs([
            PICK_BASE[0],
            PICK_BASE[1],
            PICK_BASE[2],
            *ROTATION
        ])

        move_done_check()

        indy.set_do([
            (2, True)
        ])

        time.sleep(1)

        indy.move_task_abs([
            PICK_BASE[0],
            PICK_BASE[1],
            PICK_BASE[2] + RETRACT_Z,
            *ROTATION
        ])

        move_done_check()

        indy.move_task_abs([
            place[0],
            place[1],
            place[2] + RETRACT_Z,
            *ROTATION1
        ])

        move_done_check()

        indy.move_task_abs([
            place[0],
            place[1],
            place[2],
            *ROTATION1
        ])

        move_done_check()

        indy.set_do([
            (2, False)
        ])

        time.sleep(1)

        indy.move_task_abs([
            place[0],
            place[1],
            place[2] + RETRACT_Z,
            *ROTATION1
        ])

        move_done_check()

    indy.move_home()
    move_done_check()


execute_pick_and_place()
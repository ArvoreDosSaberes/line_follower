import tkinter as tk
import math


CELL_SIZE = 5
GRID_WIDTH = 120
GRID_HEIGHT = 80
LINE_COLOR = "black"
BG_COLOR = "white"
CAR_COLOR = "red"
SENSOR_COLOR_ON = "yellow"
SENSOR_COLOR_OFF = "#888888"


class LineGrid:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.width = GRID_WIDTH
        self.height = GRID_HEIGHT
        self.cell_size = CELL_SIZE
        self.cells = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self._draw_grid()

    def _draw_grid(self):
        w = self.width * self.cell_size
        h = self.height * self.cell_size
        self.canvas.configure(width=w, height=h, bg=BG_COLOR)
        for i in range(self.width + 1):
            x = i * self.cell_size
            self.canvas.create_line(x, 0, x, h, fill="#cccccc")
        for j in range(self.height + 1):
            y = j * self.cell_size
            self.canvas.create_line(0, y, w, y, fill="#cccccc")

    def pos_to_cell(self, x, y):
        i = int(x // self.cell_size)
        j = int(y // self.cell_size)
        if 0 <= i < self.width and 0 <= j < self.height:
            return i, j
        return None

    def set_cell_line(self, i, j, value=1):
        if 0 <= i < self.width and 0 <= j < self.height:
            if self.cells[j][i] != value:
                self.cells[j][i] = value
                x0 = i * self.cell_size
                y0 = j * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                fill = LINE_COLOR if value else BG_COLOR
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="")

    def is_line_at(self, x, y):
        cell = self.pos_to_cell(x, y)
        if cell is None:
            return False
        i, j = cell
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                ii = i + di
                jj = j + dj
                if 0 <= ii < self.width and 0 <= jj < self.height:
                    if self.cells[jj][ii] == 1:
                        return True
        return False


class LineFollowerCar:
    def __init__(self, grid: LineGrid, canvas: tk.Canvas):
        self.grid = grid
        self.canvas = canvas
        self.x = grid.cell_size * 2
        self.y = grid.height * grid.cell_size - grid.cell_size * 2
        self.direction = -math.pi / 2
        self.radius = grid.cell_size * 0.8
        self.speed = grid.cell_size * 0.6
        self.angular_speed = 0.09
        self.sensor_distance = grid.cell_size * 1.2
        self.sensor_spacing = grid.cell_size * 0.6
        self.num_sensors = 6
        self.car_id = None
        self.sensor_ids = []
        self._create_graphics()

    def _create_graphics(self):
        if self.car_id is None:
            self.car_id = self.canvas.create_oval(0, 0, 0, 0, fill=CAR_COLOR, outline="black")
        for _ in range(self.num_sensors):
            self.sensor_ids.append(self.canvas.create_oval(0, 0, 0, 0, fill=SENSOR_COLOR_OFF, outline="black", width=1))
        self._redraw()

    def reset_to_start(self):
        self.x = self.grid.cell_size
        self.y = self.grid.height * self.grid.cell_size - self.grid.cell_size
        self.direction = -math.pi / 2
        self._redraw()

    def _sensor_positions(self):
        positions = []
        offsets = [(-2.5, 0), (-1.5, 0), (-0.5, 0), (0.5, 0), (1.5, 0), (2.5, 0)]
        cos_t = math.cos(self.direction)
        sin_t = math.sin(self.direction)
        fx = self.x + cos_t * self.sensor_distance
        fy = self.y + sin_t * self.sensor_distance
        for off, _ in offsets:
            lx = fx + (-sin_t) * off * self.sensor_spacing
            ly = fy + (cos_t) * off * self.sensor_spacing
            positions.append((lx, ly))
        return positions

    def read_sensors(self):
        sensor_pos = self._sensor_positions()
        readings = []
        for (sx, sy) in sensor_pos:
            on_line = self.grid.is_line_at(sx, sy)
            readings.append(1 if on_line else 0)
        return readings

    def _control_from_sensors(self, readings):
        weights = [-3, -2, -1, 1, 2, 3]
        total = 0
        active = 0
        for r, w in zip(readings, weights):
            if r:
                total += w
                active += 1
        if active == 0:
            return None
        error = total / active
        return error

    def step(self):
        readings = self.read_sensors()
        error = self._control_from_sensors(readings)
        if error is None:
            self.x += math.cos(self.direction) * self.speed
            self.y += math.sin(self.direction) * self.speed
        else:
            self.direction += self.angular_speed * error
            self.x += math.cos(self.direction) * self.speed
            self.y += math.sin(self.direction) * self.speed
        self._redraw(readings)

    def _redraw(self, readings=None):
        x0 = self.x - self.radius
        y0 = self.y - self.radius
        x1 = self.x + self.radius
        y1 = self.y + self.radius
        self.canvas.coords(self.car_id, x0, y0, x1, y1)
        sensor_pos = self._sensor_positions()
        if readings is None:
            readings = [0] * self.num_sensors
        for idx, (sx, sy) in enumerate(sensor_pos):
            r = self.grid.cell_size * 0.15
            x0 = sx - r
            y0 = sy - r
            x1 = sx + r
            y1 = sy + r
            self.canvas.coords(self.sensor_ids[idx], x0, y0, x1, y1)
            color = SENSOR_COLOR_ON if readings[idx] else SENSOR_COLOR_OFF
            self.canvas.itemconfig(self.sensor_ids[idx], fill=color)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Seguidor de Linha - 6 Sensores")
        self.canvas = tk.Canvas(root)
        self.canvas.grid(row=0, column=0, columnspan=3)
        self.grid = LineGrid(self.canvas)
        self.car = LineFollowerCar(self.grid, self.canvas)
        self.drawing = False
        self.following = False
        self._build_controls()
        self._bind_events()

    def _build_controls(self):
        self.btn_clear = tk.Button(self.root, text="Limpar", command=self.clear_grid)
        self.btn_clear.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.btn_reset = tk.Button(self.root, text="Reposicionar Carrinho", command=self.reset_car)
        self.btn_reset.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.btn_follow = tk.Button(self.root, text="Seguir Linha", command=self.toggle_follow)
        self.btn_follow.grid(row=1, column=2, sticky="ew", padx=5, pady=5)

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def on_mouse_down(self, event):
        self.drawing = True
        self._draw_at(event.x, event.y)

    def on_mouse_move(self, event):
        if self.drawing and not self.following:
            self._draw_at(event.x, event.y)

    def on_mouse_up(self, event):
        self.drawing = False

    def _draw_at(self, x, y):
        cell = self.grid.pos_to_cell(x, y)
        if cell is not None:
            i, j = cell
            self.grid.set_cell_line(i, j, 1)

    def clear_grid(self):
        for j in range(self.grid.height):
            for i in range(self.grid.width):
                self.grid.cells[j][i] = 0
        self.canvas.delete("all")
        self.grid._draw_grid()
        self.car = LineFollowerCar(self.grid, self.canvas)

    def reset_car(self):
        self.car.reset_to_start()

    def toggle_follow(self):
        if not self.following:
            self.following = True
            self.btn_follow.config(text="Parar")
            self._follow_loop()
        else:
            self.following = False
            self.btn_follow.config(text="Seguir Linha")

    def _follow_loop(self):
        if not self.following:
            return
        self.car.step()
        if not (0 <= self.car.x <= self.grid.width * self.grid.cell_size and 0 <= self.car.y <= self.grid.height * self.grid.cell_size):
            self.following = False
            self.btn_follow.config(text="Seguir Linha")
            return
        self.root.after(30, self._follow_loop)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

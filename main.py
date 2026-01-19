import time
import tkinter as tk
from PIL import ImageGrab, ImageTk
import os
from datetime import datetime

from core import DotaAuto
from config import ScreenConfig

# =========================
# НАСТРОЙКИ
# =========================
DISPLAY_WIDTH = 1200
DISPLAY_HEIGHT = 675

POINT_RADIUS = 6
POINT_COLOR_1 = "red"
POINT_COLOR_2 = "blue"
RECT_COLOR = "green"
RECT_WIDTH = 2

SCALE_X = DISPLAY_WIDTH / ScreenConfig.WIDTH
SCALE_Y = DISPLAY_HEIGHT / ScreenConfig.HEIGHT

BG_COLOR = "#2b2b2b"
PANEL_COLOR = "#1f1f1f"
BUTTON_COLOR = "#4a7a8c"
BUTTON_ACTIVE = "#5fa3bb"

# =========================
# Лупа
# =========================
ZOOM_RADIUS = 30  # радиус области вокруг точки
ZOOM_SCALE = 3    # масштаб увеличения

# =========================
# TKINTER APP
# =========================
class FindPointsApp:
    def __init__(self, root, image, original_image):
        self.root = root
        self.root.title("DotaAuto. Определение координат")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(DISPLAY_WIDTH, DISPLAY_HEIGHT)

        # Иконка
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        try:
            icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Не удалось загрузить иконку: {e}")

        # Сохраняем оригинальный скриншот
        self.original_screenshot = original_image

        # Масштабируем изображение для Canvas
        self.image = image.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.canvas = tk.Canvas(
            root,
            width=DISPLAY_WIDTH,
            height=DISPLAY_HEIGHT,
            cursor="cross",
            bg=BG_COLOR,
            highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.point1 = None
        self.point2 = None
        self.rect = None
        self.dragging_point = None
        self.pick_mode = False

        self.status_label = tk.Label(
            root, text="Нажмите «Выставить координаты»",
            fg="white", bg=PANEL_COLOR
        )
        self.status_label.pack(fill="x", pady=(6, 2))

        self.coords_label = tk.Label(
            root, text="Point1: - | Point2: -",
            fg="white", bg=PANEL_COLOR
        )
        self.coords_label.pack(fill="x")

        self.size_label = tk.Label(
            root, text="Размер: - x -",
            fg="white", bg=PANEL_COLOR
        )
        self.size_label.pack(fill="x")

        # Frame для кнопок по центру
        self.button_frame = tk.Frame(root, bg=BG_COLOR)
        self.button_frame.pack(pady=10)

        # Кнопка выставления координат
        self.pick_button = tk.Button(
            self.button_frame,
            text="Выставить координаты",
            command=self.enable_pick_mode,
            bg=BUTTON_COLOR,
            fg="white",
            activebackground=BUTTON_ACTIVE,
            relief="raised",
            width=25
        )
        self.pick_button.pack(side="left")

        # Кнопка копирования (изначально скрыта)
        self.copy_button = tk.Button(
            self.button_frame,
            text="Скопировать",
            command=self.copy_coords,
            bg=BUTTON_COLOR,
            fg="white",
            activebackground=BUTTON_ACTIVE,
            relief="raised",
            width=15
        )
        self.copy_button.pack(side="left", padx=(10, 0))
        self.copy_button.pack_forget()

        # Кнопка экспорта (изначально скрыта)
        self.export_button = tk.Button(
            self.button_frame,
            text="Экспорт",
            command=self.export_region,
            bg=BUTTON_COLOR,
            fg="white",
            activebackground=BUTTON_ACTIVE,
            relief="raised",
            width=15
        )
        self.export_button.pack(side="left", padx=(10, 0))
        self.export_button.pack_forget()

        # бинды
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)

        # Бинды клавиш для точного перемещения стрелками
        self.root.bind("<Up>", self.on_arrow_key)
        self.root.bind("<Down>", self.on_arrow_key)
        self.root.bind("<Left>", self.on_arrow_key)
        self.root.bind("<Right>", self.on_arrow_key)

        # Лупа
        self.zoom_window = None
        self.tk_zoom = None

    # =========================
    # Режим выбора координат
    # =========================
    def enable_pick_mode(self):
        self.pick_mode = True
        self.point1 = None
        self.point2 = None
        self.rect = None
        self.dragging_point = None
        self.canvas.delete("point")
        self.canvas.delete("rect")
        self.update_labels()
        self.status_label.config(text="ПКМ — поставить 2 точки")
        self.copy_button.pack_forget()
        self.export_button.pack_forget()

    # =========================
    # ПКМ — выставление точек
    # =========================
    def on_right_click(self, event):
        if not self.pick_mode:
            return

        x, y = self.clamp_center(event.x, event.y)

        if self.point1 is None:
            self.point1 = self.create_point(x, y, POINT_COLOR_1)
            self.status_label.config(text="ПКМ — поставить вторую точку")
        elif self.point2 is None:
            self.point2 = self.create_point(x, y, POINT_COLOR_2)
            self.pick_mode = False
            self.status_label.config(text="ЛКМ — перетаскивание точек")
            self.copy_button.pack(side="left", padx=(10, 0))
            self.export_button.pack(side="left", padx=(10, 0))

        self.update_rectangle()
        self.update_labels()

    # =========================
    # Создание точки
    # =========================
    def create_point(self, x, y, color):
        return self.canvas.create_oval(
            x - POINT_RADIUS,
            y - POINT_RADIUS,
            x + POINT_RADIUS,
            y + POINT_RADIUS,
            fill=color,
            outline="black",
            tags=("point",)
        )

    # =========================
    # Перетаскивание точек
    # =========================
    def on_left_press(self, event):
        for item in self.canvas.find_overlapping(event.x, event.y, event.x, event.y):
            if "point" in self.canvas.gettags(item):
                self.dragging_point = item
                # НЕ создаём лупу сразу
                break

    def on_drag(self, event):
        if not self.dragging_point:
            return

        x, y = self.clamp_center(event.x, event.y)

        self.canvas.coords(
            self.dragging_point,
            x - POINT_RADIUS,
            y - POINT_RADIUS,
            x + POINT_RADIUS,
            y + POINT_RADIUS
        )

        self.update_rectangle()
        self.update_labels()

        # Создаём лупу только при первом движении
        if not self.zoom_window:
            self.create_zoom_window()

        self.update_zoom_window(x, y)

    def on_release(self, event):
        self.dragging_point = None
        if self.zoom_window:
            self.zoom_window.destroy()
            self.zoom_window = None

    # =========================
    # Курсор мыши
    # =========================
    def on_motion(self, event):
        for item in self.canvas.find_overlapping(event.x, event.y, event.x, event.y):
            if "point" in self.canvas.gettags(item):
                self.canvas.config(cursor="hand2")
                return
        self.canvas.config(cursor="cross")

    # =========================
    # Ограничение точек внутри Canvas
    # =========================
    def clamp_center(self, x, y):
        x = min(max(0, x), DISPLAY_WIDTH)
        y = min(max(0, y), DISPLAY_HEIGHT)
        return x, y

    # =========================
    # Получение координат точки
    # =========================
    def get_point_coords(self, point):
        if not point:
            return None
        x1, y1, x2, y2 = self.canvas.coords(point)
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    # =========================
    # Обновление прямоугольника
    # =========================
    def update_rectangle(self):
        if not self.point1 or not self.point2:
            return

        x1, y1 = self.get_point_coords(self.point1)
        x2, y2 = self.get_point_coords(self.point2)

        if self.rect:
            self.canvas.coords(self.rect, x1, y1, x2, y2)
        else:
            self.rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=RECT_COLOR,
                width=RECT_WIDTH,
                tags=("rect",)
            )

    # =========================
    # Обновление меток
    # =========================
    def update_labels(self):
        def unscale(p):
            if not p:
                return "-"
            x = int(p[0] / SCALE_X)
            y = int(p[1] / SCALE_Y)
            return x, y

        p1 = self.get_point_coords(self.point1)
        p2 = self.get_point_coords(self.point2)

        self.coords_label.config(
            text=f"Point1: {unscale(p1)} | Point2: {unscale(p2)}"
        )

        if p1 and p2:
            width = abs(p2[0] - p1[0]) / SCALE_X
            height = abs(p2[1] - p1[1]) / SCALE_Y
            self.size_label.config(
                text=f"Размер: {int(width)} x {int(height)}"
            )
        else:
            self.size_label.config(text="Размер: - x -")

    # =========================
    # Копирование координат
    # =========================
    def copy_coords(self):
        p1 = self.get_point_coords(self.point1)
        p2 = self.get_point_coords(self.point2)

        if not p1 or not p2:
            return

        x1, y1 = int(p1[0] / SCALE_X), int(p1[1] / SCALE_Y)
        x2, y2 = int(p2[0] / SCALE_X), int(p2[1] / SCALE_Y)

        coords_text = f"Point1: ({x1}, {y1}) | Point2: ({x2}, {y2})"

        self.root.clipboard_clear()
        self.root.clipboard_append(coords_text)
        self.root.update()

        self.status_label.config(text="Координаты скопированы!")

    # =========================
    # Экспорт выделенной области с новым форматом имени
    # =========================
    def export_region(self):
        p1 = self.get_point_coords(self.point1)
        p2 = self.get_point_coords(self.point2)

        if not p1 or not p2:
            return

        # Координаты в оригинальном размере
        x1 = int(p1[0] / SCALE_X)
        y1 = int(p1[1] / SCALE_Y)
        x2 = int(p2[0] / SCALE_X)
        y2 = int(p2[1] / SCALE_Y)

        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)

        export_dir = os.path.join(os.path.dirname(__file__), "export")
        os.makedirs(export_dir, exist_ok=True)

        # Формируем имя файла: dd.mm.yy_left.top_right.bottom.png
        now = datetime.now()
        date_str = now.strftime("%d.%m.%y")
        filename = f"{date_str}_{left}.{top}_{right}.{bottom}.png"
        filepath = os.path.join(export_dir, filename)

        region = self.original_screenshot.crop((left, top, right, bottom))
        region.save(filepath)

        self.status_label.config(text=f"Область экспортирована: {filename}")

    # =========================
    # Лупа с сеткой и точкой в центре + координаты
    # =========================
    def create_zoom_window(self):
        self.zoom_window = tk.Toplevel(self.root)
        self.zoom_window.overrideredirect(True)
        self.zoom_window.attributes("-topmost", True)

        # Canvas для изображения
        self.zoom_canvas = tk.Canvas(
            self.zoom_window,
            width=ZOOM_RADIUS*2*ZOOM_SCALE,
            height=ZOOM_RADIUS*2*ZOOM_SCALE,
            bg="white"
        )
        self.zoom_canvas.pack()

        # Label для координат под Canvas
        self.coord_label = tk.Label(
            self.zoom_window,
            text="(x, y)",
            bg="#333333",
            fg="white",
            font=("Arial", 10)
        )
        self.coord_label.pack(fill="x")

    def update_zoom_window(self, x, y):
        orig_x = int(x / SCALE_X)
        orig_y = int(y / SCALE_Y)

        left = max(0, orig_x - ZOOM_RADIUS)
        top = max(0, orig_y - ZOOM_RADIUS)
        right = min(ScreenConfig.WIDTH, orig_x + ZOOM_RADIUS)
        bottom = min(ScreenConfig.HEIGHT, orig_y + ZOOM_RADIUS)

        region = self.original_screenshot.crop((left, top, right, bottom))
        region = region.resize((ZOOM_RADIUS*2*ZOOM_SCALE, ZOOM_RADIUS*2*ZOOM_SCALE))
        self.tk_zoom = ImageTk.PhotoImage(region)
        self.zoom_canvas.delete("all")
        self.zoom_canvas.create_image(0, 0, anchor="nw", image=self.tk_zoom)

        # ======= Сетка =======
        w = ZOOM_RADIUS * 2 * ZOOM_SCALE
        h = ZOOM_RADIUS * 2 * ZOOM_SCALE
        self.zoom_canvas.create_line(w//2, 0, w//2, h, fill="white")
        self.zoom_canvas.create_line(0, h//2, w, h//2, fill="white")
        # Центр лупы
        self.zoom_canvas.create_oval(w//2-2, h//2-2, w//2+2, h//2+2, fill="red", outline="red")

        # Обновляем координаты под лупой
        self.coord_label.config(text=f"({orig_x}, {orig_y})")

        # Позиция окна лупы рядом с курсором
        screen_x = self.root.winfo_pointerx() + 20
        screen_y = self.root.winfo_pointery() - h//2
        self.zoom_window.geometry(f"+{screen_x}+{screen_y}")

    # =========================
    # Перемещение стрелками на 1 px
    # =========================
    def on_arrow_key(self, event):
        if not self.dragging_point:
            return

        dx, dy = 0, 0
        if event.keysym == "Up":
            dy = -1
        elif event.keysym == "Down":
            dy = 1
        elif event.keysym == "Left":
            dx = -1
        elif event.keysym == "Right":
            dx = 1

        x1, y1, x2, y2 = self.canvas.coords(self.dragging_point)
        cx = (x1 + x2)/2 + dx
        cy = (y1 + y2)/2 + dy
        cx, cy = self.clamp_center(cx, cy)

        self.canvas.coords(
            self.dragging_point,
            cx - POINT_RADIUS,
            cy - POINT_RADIUS,
            cx + POINT_RADIUS,
            cy + POINT_RADIUS
        )

        self.update_rectangle()
        self.update_labels()
        self.update_zoom_window(cx, cy)


# =========================
# MAIN
# =========================
def main():
    DotaAuto.window.focus()
    time.sleep(0.3)

    win = DotaAuto.window._get_dota_window()
    screenshot = ImageGrab.grab(
        bbox=(win.left, win.top, win.left + ScreenConfig.WIDTH, win.top + ScreenConfig.HEIGHT)
    )

    root = tk.Tk()
    app = FindPointsApp(root, screenshot, screenshot)
    root.mainloop()


if __name__ == "__main__":
    main()

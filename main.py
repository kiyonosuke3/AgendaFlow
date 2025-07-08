import flet as ft
import os
import json
import datetime

APP_NAME = "AgendaFlow"
DEFAULT_SETTINGS = {
    "theme_settings": {"theme_mode": "LIGHT", "theme_color": "BLUE"},
    "projects": ["Default"],
    "last_project": "Default",
}


class SettingsManager:
    def __init__(self):
        self.file = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "settings.json")
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        self.load()

    def load(self):
        if os.path.isfile(self.file):
            with open(self.file, encoding="utf-8") as f:
                self.data = {**DEFAULT_SETTINGS, **json.load(f)}
        else:
            self.data = DEFAULT_SETTINGS.copy()
        self.save()

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, key):
        return self.data[key]

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get_theme_mode(self):
        return self.data["theme_settings"].get("theme_mode", "LIGHT")

    def get_theme_color(self):
        return self.data["theme_settings"].get("theme_color", "BLUE")

    def set_theme(self, mode, color):
        self.data["theme_settings"]["theme_mode"] = mode
        self.data["theme_settings"]["theme_color"] = color
        self.save()


class TodoManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def fname(self, project):
        n = "".join(c if c.isalnum() else "_" for c in project)
        return os.path.join(self.data_dir, f"todos_{n}.json")

    def load(self, project):
        fn = self.fname(project)
        if os.path.isfile(fn):
            with open(fn, encoding="utf-8") as f:
                return json.load(f)
        return []

    def save(self, project, todos):
        with open(self.fname(project), "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class AgendaFlowApp:
    THEME_COLORS = {
        "BLUE": ft.Colors.BLUE,
        "RED": ft.Colors.RED,
        "GREEN": ft.Colors.GREEN,
        "PINK": ft.Colors.PINK_500,
        "PURPLE": ft.Colors.PURPLE,
        "ORANGE": ft.Colors.ORANGE,
        "INDIGO": ft.Colors.INDIGO,
        "BROWN": ft.Colors.BROWN,
        "CYAN": ft.Colors.CYAN,
        "TEAL": ft.Colors.TEAL,
    }

    def __init__(self, page: ft.Page):
        self.page = page
        self.settings = SettingsManager()
        self.todos_mgr = TodoManager(os.path.dirname(self.settings.file))
        self.projects = self.settings.get("projects")
        self.current_project = (
            self.settings.get("last_project")
            if self.settings.get("last_project") in self.projects
            else self.projects[0]
        )
        self.todos = self.todos_mgr.load(self.current_project)
        self.tf_states = {}

        self.setup_components()
        self.setup_page()
        self.setup_bindings()
        self.update_theme()
        self.update_project_dropdown()
        self.update_todo_list()
        self.update_filled()

    def setup_components(self):
        dark_mode = self.settings.get_theme_mode() == "DARK"
        theme_color = self.settings.get_theme_color()
        self.input_box = ft.TextField(expand=True, multiline=True, min_lines=1, hint_text="Memo", filled=dark_mode)
        self.add_btn = ft.ElevatedButton("+ Add", width=70)
        self.proj_dd = ft.Dropdown(
            options=[ft.dropdown.Option(p) for p in self.projects],
            value=self.current_project,
            width=200,
            filled=False,  # Always False
            border=ft.InputBorder.NONE,  # Always no border
        )
        self.mode_btn = ft.IconButton(
            icon=ft.Icons.DARK_MODE, selected_icon=ft.Icons.LIGHT_MODE, selected=dark_mode, data="theme"
        )
        self.color_dd = ft.Dropdown(
            label="Theme Color",
            options=[ft.dropdown.Option(k) for k in self.THEME_COLORS.keys()],
            value=theme_color,
            width=120,
            data="color",
            filled=dark_mode,
        )
        self.todo_list = ft.Column(expand=True, scroll="auto")

    def setup_page(self):
        self.page.title = APP_NAME
        self.page.window_maximized = True
        self.page.theme_mode = getattr(ft.ThemeMode, self.settings.get_theme_mode())
        self.page.theme = ft.Theme(
            color_scheme_seed=self.THEME_COLORS.get(self.settings.get_theme_color(), ft.Colors.BLUE)
        )
        self.page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            self.proj_dd,
                            ft.Container(expand=True),
                            ft.Row(
                                [
                                    ft.IconButton(icon=ft.Icons.ADD, tooltip="Add Project", on_click=self.add_proj),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE, tooltip="Delete Project", on_click=self.del_proj
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row([self.input_box, self.add_btn], spacing=8),
                    ft.Container(self.todo_list, expand=True, padding=8),
                ],
                expand=True,
                spacing=5,
            )
        )
        self.page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.SETTINGS, mini=True, tooltip="Settings", on_click=self.open_setting
        )

    def setup_bindings(self):
        self.add_btn.on_click = self.add_todo
        self.input_box.on_submit = self.add_todo
        self.proj_dd.on_change = self.change_proj
        self.mode_btn.on_click = self.change_theme
        self.color_dd.on_change = self.change_theme

    def update_theme(self):
        mode = "DARK" if self.mode_btn.selected else "LIGHT"
        col = self.color_dd.value
        self.page.theme_mode = getattr(ft.ThemeMode, mode)
        self.page.theme = ft.Theme(color_scheme_seed=self.THEME_COLORS.get(col, ft.Colors.BLUE))
        self.settings.set_theme(mode, col)
        self.update_filled()
        self.page.update()

    def update_filled(self):
        dark = self.mode_btn.selected
        self.input_box.filled = dark  # Only True if dark
        self.color_dd.filled = dark

    def update_project_dropdown(self):
        self.proj_dd.options = [ft.dropdown.Option(p) for p in self.settings.get("projects")]
        self.proj_dd.value = self.current_project

    def update_todo_list(self):
        self.todo_list.controls.clear()
        self.tf_states.clear()
        for t in self.sort_todos(self.todos):
            idx = self.todos.index(t)
            is_done, is_imp = t.get("done"), t.get("important")
            fg = ft.Colors.with_opacity(0.5 if is_done else 1, ft.Colors.ON_PRIMARY_CONTAINER)
            txt = ft.TextField(
                value=t["text"],
                expand=True,
                multiline=True,
                min_lines=1,
                read_only=is_done,
                on_change=lambda e, ix=idx: self.tf_states.setdefault(ix, e.control.value),
                on_blur=lambda e, ix=idx: (
                    self.todos[ix].update(text=e.control.value),
                    self.todos_mgr.save(self.current_project, self.todos),
                ),
                text_style=ft.TextStyle(color=fg, weight="bold" if is_imp else None, size=15),
                border=ft.InputBorder.NONE,
                filled=False,
            )
            self.tf_states[idx] = t["text"]
            done_info = (
                ft.Text(f"Completed: {t['done_date']}", color=fg, size=12)
                if is_done and t.get("done_date")
                else ft.Container()
            )
            row = ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.STAR if is_imp else ft.Icons.STAR_BORDER,
                                    tooltip="Important" if not is_imp else "Remove",
                                    disabled=is_done,
                                    on_click=lambda e, ix=idx: self.on_imp_toggle(ix),
                                ),
                                txt,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        done_info,
                    ],
                    spacing=2,
                ),
                bgcolor=ft.Colors.with_opacity(0.6 if is_done else 1, ft.Colors.ON_PRIMARY),
                border_radius=6,
                border=ft.border.all(1, "#eee"),
                padding=10,
            )

            # Add Dismissible: wrap row container
            def make_on_confirm_dismiss(ix):
                def on_confirm_dismiss(e):
                    direction = e.direction
                    is_done = self.todos[ix].get("done", False)

                    def cb_dismiss(ok):
                        e.control.confirm_dismiss(ok)
                        self.page.update()

                    if direction == ft.DismissDirection.START_TO_END:
                        if not is_done:

                            def ok_():
                                cb_dismiss(True)
                                self.func_complete(ix)

                            def cancel_():
                                cb_dismiss(False)

                            self.open_confirm_dialog("Mark as complete?", "Set this memo as completed.", ok_, cancel_)
                        else:

                            def ok_():
                                cb_dismiss(True)
                                self.func_uncomplete(ix)

                            def cancel_():
                                cb_dismiss(False)

                            self.open_confirm_dialog(
                                "Mark as incomplete?", "Return this memo to incomplete state.", ok_, cancel_
                            )
                    elif direction == ft.DismissDirection.END_TO_START:

                        def ok_():
                            cb_dismiss(True)
                            self.func_delete(ix)

                        def cancel_():
                            cb_dismiss(False)

                        self.open_confirm_dialog("Delete memo?", "Delete this memo.", ok_, cancel_)
                    else:
                        cb_dismiss(False)

                return on_confirm_dismiss

            self.todo_list.controls.append(
                ft.Dismissible(
                    row,
                    key=str(idx),
                    on_confirm_dismiss=make_on_confirm_dismiss(idx),
                    dismiss_thresholds={
                        ft.DismissDirection.START_TO_END: 0.15,
                        ft.DismissDirection.END_TO_START: 0.15,
                    },
                    background=ft.Container(
                        ft.Row(
                            [ft.Icon(name="check", color=ft.Colors.TEAL, size=24)],
                            alignment=ft.MainAxisAlignment.START,
                            expand=True,
                        ),
                        bgcolor=ft.Colors.TEAL_100,
                    ),
                    secondary_background=ft.Container(
                        ft.Row(
                            [ft.Icon(name="delete", color=ft.Colors.RED, size=24)],
                            alignment=ft.MainAxisAlignment.END,
                            expand=True,
                        ),
                        bgcolor=ft.Colors.RED_100,
                    ),
                )
            )
        self.page.update()

    def on_imp_toggle(self, idx):
        todo = self.todos[idx]
        if todo.get("important"):
            todo["important"] = False
        else:
            count = sum(1 for t in self.todos if t.get("important") and not t.get("done"))
            if count >= 6:
                self.page.open(ft.SnackBar(ft.Text("Max 6 important memos")))
                self.page.update()
                return
            todo["important"] = True
        self.save_and_refresh()

    @staticmethod
    def sort_todos(ts):
        return (
            [t for t in ts if t.get("important") and not t.get("done")]
            + [t for t in ts if not t.get("important") and not t.get("done")]
            + [t for t in ts if t.get("done")]
        )

    def save_and_refresh(self):
        self.todos_mgr.save(self.current_project, self.todos)
        self.update_todo_list()

    def func_complete(self, idx):
        t = self.todos[idx]
        if not t.get("done"):
            t["done"] = True
            t["done_date"] = now()
            t["important"] = False
        self.save_and_refresh()

    def func_uncomplete(self, idx):
        t = self.todos[idx]
        if t.get("done"):
            t["done"] = False
            t["done_date"] = ""
        self.save_and_refresh()

    def func_delete(self, idx):
        self.todos.pop(idx)
        self.save_and_refresh()

    def open_confirm_dialog(self, title, content, on_ok, on_cancel=None):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton(
                    "Cancel", on_click=lambda e: (on_cancel() if on_cancel else None, self.page.close(dialog))
                ),
                ft.ElevatedButton("OK", on_click=lambda e: (on_ok(), self.page.close(dialog))),
            ],
            actions_alignment="end",
        )
        self.page.open(dialog)

    def add_todo(self, e=None):
        val = self.input_box.value.strip()
        if not val:
            return
        self.todos.append({"text": val, "important": False, "done": False, "done_date": ""})
        self.input_box.value = ""
        self.save_and_refresh()

    def change_proj(self, e=None):
        self.current_project = self.proj_dd.value
        self.settings.set("last_project", self.current_project)
        self.todos = self.todos_mgr.load(self.current_project)
        self.update_todo_list()

    def add_proj(self, e=None):
        inp = ft.TextField(label="New project name", width=250, filled=self.mode_btn.selected)

        def ok(ev):
            name = inp.value.strip()
            if not name or name in self.settings.get("projects"):
                self.page.open(ft.SnackBar(ft.Text("Please input a new name.")))
                return
            projs = self.settings.get("projects")
            projs.append(name)
            self.settings.set("projects", projs)
            self.current_project = name
            self.settings.set("last_project", self.current_project)
            self.update_project_dropdown()
            self.todos = self.todos_mgr.load(self.current_project)
            self.update_todo_list()
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Add Project"),
            content=inp,
            actions=[
                ft.ElevatedButton("Add", on_click=ok),
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dialog)),
            ],
            actions_alignment="end",
        )
        self.page.open(dialog)

    def del_proj(self, e=None):
        if self.current_project == "Default":
            self.page.open(ft.SnackBar(ft.Text("Default cannot be deleted")))
            return

        def do_del(ev):
            projs = self.settings.get("projects")
            idx = projs.index(self.current_project)
            projs.remove(self.current_project)
            self.settings.set("projects", projs)
            fn = self.todos_mgr.fname(self.current_project)
            if os.path.exists(fn):
                os.remove(fn)
            if projs:
                new_proj = projs[idx - 1] if idx > 0 else projs[0]
            else:
                new_proj = "Default"
                self.settings.set("projects", ["Default"])
            self.current_project = new_proj
            self.settings.set("last_project", self.current_project)
            self.update_project_dropdown()
            self.todos = self.todos_mgr.load(self.current_project)
            self.update_todo_list()
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Confirmation"),
            content=ft.Text(f'Delete "{self.current_project}"?'),
            actions=[
                ft.ElevatedButton("Delete", on_click=do_del),
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dialog)),
            ],
            actions_alignment="end",
        )
        self.page.open(dialog)

    def open_setting(self, e=None):
        d = ft.AlertDialog(
            title=ft.Text("Display Settings"),
            content=ft.Row([self.color_dd, self.mode_btn]),
            actions=[ft.TextButton("Close", on_click=lambda e: self.page.close(d))],
            actions_alignment="end",
        )
        self.page.open(d)

    def change_theme(self, e=None):
        if e and getattr(e.control, "data", None) == "theme":
            self.mode_btn.selected = not self.mode_btn.selected
        self.update_theme()
        self.update_todo_list()
        self.update_filled()


def main(page: ft.Page):
    AgendaFlowApp(page)


if __name__ == "__main__":
    ft.app(target=main)

import flet as ft
import os
import json
import datetime

APP_NAME = "AgendaFlow"
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
DATA_DIR = os.path.join(LOCALAPPDATA, APP_NAME)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "theme_settings": {"theme_mode": "LIGHT", "theme_color": "BLUE"},
    "projects": ["Default"],
    "last_project": "Default",
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 初回起動・不完全データ補完
                for key in DEFAULT_SETTINGS:
                    if key not in data:
                        data[key] = DEFAULT_SETTINGS[key]
                return data
        except Exception:
            return DEFAULT_SETTINGS.copy()
    else:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def project_file(project):
    safe_name = "".join(c if c.isalnum() else "_" for c in project)
    return os.path.join(DATA_DIR, f"todos_{safe_name}.json")


def load_todos(project_name):
    file = project_file(project_name)
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_todos(project_name, todos):
    file = project_file(project_name)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def main(page: ft.Page):
    page.title = "AgendaFlow"
    page.window_maximized = True
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.MainAxisAlignment.START

    THEME_COLORS = [
        ("BLUE", ft.Colors.BLUE),
        ("RED", ft.Colors.RED),
        ("GREEN", ft.Colors.GREEN),
        ("PINK", ft.Colors.PINK_500),
        ("PURPLE", ft.Colors.PURPLE),
        ("ORANGE", ft.Colors.ORANGE),
        ("INDIGO", ft.Colors.INDIGO),
        ("BROWN", ft.Colors.BROWN),
        ("CYAN", ft.Colors.CYAN),
        ("TEAL", ft.Colors.TEAL),
    ]

    # 設定を一括ロード
    settings = load_settings()
    projects = settings.get("projects", ["Default"])
    theme_settings = settings.get("theme_settings", DEFAULT_SETTINGS["theme_settings"])
    last_project = settings.get("last_project", None)

    current_theme_mode = theme_settings.get("theme_mode", "LIGHT")
    current_theme_color = theme_settings.get("theme_color", "BLUE")
    page.theme_mode = getattr(ft.ThemeMode, current_theme_mode)
    page.theme = ft.Theme(color_scheme_seed=dict(THEME_COLORS)[current_theme_color])

    current_project = last_project if (last_project in projects) else (projects[0] if projects else "Default")
    todos = load_todos(current_project)
    textfields_state = {}  # idx: value

    todo_list = ft.Column(scroll="auto", expand=True, spacing=6)
    todo_input = ft.TextField(
        hint_text="メモ内容",
        expand=True,
        multiline=True,
        min_lines=2,
        filled=True if current_theme_mode == "DARK" else False,
    )
    add_todo_btn = ft.ElevatedButton("+ 追加", width=70)

    project_name_input = ft.TextField(label="新規プロジェクト名", width=240)
    add_project_dialog = None
    confirm_delete_dialog = None

    setting_dialog = None

    theme_mode_switch = ft.IconButton(
        icon=ft.Icons.DARK_MODE,
        icon_color=ft.Colors.PRIMARY,
        selected_icon=ft.Icons.LIGHT_MODE,
        selected_icon_color=ft.Colors.PRIMARY,
        selected=current_theme_mode == "DARK",
        data="theme",
    )
    theme_color_dropdown = ft.Dropdown(
        label="テーマ色",
        options=[ft.dropdown.Option(k, text=k) for k, _ in THEME_COLORS],
        value=current_theme_color,
        width=120,
        data="color",
    )

    # ----- 設定の保存系を一括で管理 -----
    def set_last_project(val):
        settings["last_project"] = val
        save_settings(settings)

    def on_theme_setting_change(e=None):
        if e.control.data == "theme":
            theme_mode_switch.selected = not theme_mode_switch.selected
            todo_input.filled = not todo_input.filled
            page.update()
        theme_mode_val = "DARK" if theme_mode_switch.selected else "LIGHT"
        sel_color = theme_color_dropdown.value
        for k, v in THEME_COLORS:
            if k == sel_color:
                color_seed = v
                break
        else:
            color_seed = ft.Colors.BLUE

        page.theme_mode = getattr(ft.ThemeMode, theme_mode_val)
        page.theme = ft.Theme(color_scheme_seed=color_seed)
        settings["theme_settings"]["theme_mode"] = theme_mode_val
        settings["theme_settings"]["theme_color"] = sel_color
        save_settings(settings)
        page.update()

    theme_mode_switch.on_click = on_theme_setting_change
    theme_color_dropdown.on_change = on_theme_setting_change

    def open_setting_dialog(e=None):
        nonlocal setting_dialog

        setting_dialog = ft.AlertDialog(
            title=ft.Text("表示設定"),
            content=ft.Row(
                [theme_color_dropdown, theme_mode_switch],
            ),
            actions=[
                ft.TextButton("閉じる", on_click=lambda e: page.close(setting_dialog)),
            ],
            actions_alignment="end",
        )
        page.open(setting_dialog)

    fab = ft.FloatingActionButton(
        icon=ft.Icons.SETTINGS,
        mini=True,
        tooltip="設定",
        on_click=open_setting_dialog,
    )

    def on_edit_blur(idx, e):
        value = e.control.value
        todos[idx]["text"] = value
        save_todos(current_project, todos)

    def on_window_event(e: ft.WindowEvent):
        for idx, t in enumerate(todos):
            if idx in textfields_state:
                t["text"] = textfields_state[idx]
        save_todos(current_project, todos)
        set_last_project(current_project)

    page.on_window_event = on_window_event

    def open_confirm_dialog(title, content, on_ok, on_cancel=None):
        dialog = None

        def handle_ok(e):
            on_ok()
            page.close(dialog)

        def handle_cancel(e):
            if on_cancel:
                on_cancel()
            page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton("キャンセル", on_click=handle_cancel),
                ft.ElevatedButton("OK", on_click=handle_ok),
            ],
            actions_alignment="end",
        )
        page.open(dialog)

    def sort_todos(tlist):
        imp = [t for t in tlist if t.get("important") and not t.get("done")]
        nor = [t for t in tlist if not t.get("important") and not t.get("done")]
        done = [t for t in tlist if t.get("done")]
        return imp + nor + done

    def update_todo_list():
        todo_list.controls.clear()
        sorted_todos = sort_todos(todos)
        textfields_state.clear()

        def make_on_confirm_dismiss(ix):
            def on_confirm_dismiss(e):
                direction = e.direction
                is_done = todos[ix].get("done", False)

                def cb_dismiss(ok):
                    e.control.confirm_dismiss(ok)
                    page.update()

                if direction == ft.DismissDirection.START_TO_END:
                    if not is_done:

                        def ok_():
                            cb_dismiss(True)
                            func_complete(ix)

                        def cancel_():
                            cb_dismiss(False)

                        open_confirm_dialog("完了にしますか？", "このメモを完了状態にします。", ok_, cancel_)
                    else:

                        def ok_():
                            cb_dismiss(True)
                            func_uncomplete(ix)

                        def cancel_():
                            cb_dismiss(False)

                        open_confirm_dialog("未完了にもどしますか？", "このメモを未完了状態に戻します。", ok_, cancel_)
                elif direction == ft.DismissDirection.END_TO_START:

                    def ok_():
                        cb_dismiss(True)
                        func_delete(ix)

                    def cancel_():
                        cb_dismiss(False)

                    open_confirm_dialog("削除しますか？", "このメモを削除します。", ok_, cancel_)
                else:
                    cb_dismiss(False)

            return on_confirm_dismiss

        for idx, todo in enumerate(sorted_todos):
            real_idx = todos.index(todo)
            is_done = todo.get("done")
            is_important = todo.get("important")
            text = todo.get("text")
            done_date = todo.get("done_date", "")
            fgcolor = ft.Colors.with_opacity(0.5 if is_done else 1, ft.Colors.ON_PRIMARY_CONTAINER)
            font_weight = "bold" if is_important else None

            def on_change(e, ix=real_idx):
                textfields_state[ix] = e.control.value

            txt_elem = ft.TextField(
                value=text,
                expand=True,
                multiline=True,
                min_lines=1,
                read_only=is_done,
                on_change=on_change,
                on_blur=lambda e, ix=real_idx: on_edit_blur(ix, e),
                text_style=ft.TextStyle(color=fgcolor, weight=font_weight, size=15),
                border=ft.InputBorder.NONE,
                filled=False,
            )
            textfields_state[real_idx] = text
            done_elem = (
                ft.Text(f"完了日時: {done_date}" if is_done and done_date else "", color=fgcolor, size=12)
                if is_done and done_date
                else None
            )
            todo_row = ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.STAR if is_important else ft.Icons.STAR_BORDER,
                                    tooltip="重要にする" if not is_important else "重要解除",
                                    disabled=is_done,
                                    on_click=lambda e, ix=real_idx: on_imp_toggle(ix),
                                ),
                                txt_elem,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        done_elem if done_elem else ft.Container(),
                    ],
                    spacing=2,
                ),
                bgcolor=ft.Colors.with_opacity(0.6 if is_done else 1, ft.Colors.ON_PRIMARY),
                border_radius=6,
                border=ft.border.all(1, "#eeeeee"),
                padding=10,
            )
            todo_dismiss = ft.Dismissible(
                todo_row,
                key=str(real_idx),
                on_confirm_dismiss=make_on_confirm_dismiss(real_idx),
                dismiss_thresholds={
                    ft.DismissDirection.START_TO_END: 0.15,
                    ft.DismissDirection.END_TO_START: 0.15,
                },
                background=ft.Container(
                    ft.Row(
                        [
                            ft.Icon(name="check", color=ft.Colors.TEAL, size=24),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        expand=True,
                    ),
                    bgcolor=ft.Colors.TEAL_100,
                ),
                secondary_background=ft.Container(
                    ft.Row(
                        [
                            ft.Icon(name="delete", color=ft.Colors.RED, size=24),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        expand=True,
                    ),
                    bgcolor=ft.Colors.RED_100,
                ),
            )
            todo_list.controls.append(todo_dismiss)
        page.update()

    def func_complete(idx):
        t = todos[idx]
        if not t.get("done"):
            t["done"] = True
            t["done_date"] = now_str()
            t["important"] = False
        save_and_refresh()

    def func_uncomplete(idx):
        t = todos[idx]
        if t.get("done"):
            t["done"] = False
            t["done_date"] = ""
        save_and_refresh()

    def func_delete(idx):
        todos.pop(idx)
        save_and_refresh()

    def save_and_refresh():
        save_todos(current_project, todos)
        update_todo_list()

    def on_add_todo(e):
        val = todo_input.value.strip()
        if not val:
            return
        todos.append({"text": val, "important": False, "done": False, "done_date": ""})
        todo_input.value = ""
        save_and_refresh()

    def on_imp_toggle(idx):
        todo = todos[idx]
        if todo["important"]:
            todo["important"] = False
        else:
            count = sum(1 for t in todos if t.get("important") and not t.get("done"))
            if count >= 6:
                page.open(ft.SnackBar(ft.Text("重要メモは6件まで指定できます")))
                page.update()
                return
            todo["important"] = True
        save_and_refresh()

    def update_project_dropdown():
        project_dropdown.options = [ft.dropdown.Option(p) for p in settings["projects"]]
        project_dropdown.value = current_project

    def on_project_change(e=None):
        nonlocal current_project, todos
        current_project = project_dropdown.value
        set_last_project(current_project)
        todos.clear()
        todos.extend(load_todos(current_project))
        update_todo_list()

    project_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(p) for p in settings["projects"]],
        value=current_project,
        width=200,
        border=ft.InputBorder.NONE,
        on_change=on_project_change,
    )

    add_project_btn = ft.IconButton(
        icon=ft.Icons.ADD, tooltip="プロジェクト追加", on_click=lambda e: open_add_project_dialog()
    )
    del_project_btn = ft.IconButton(
        icon=ft.Icons.DELETE, tooltip="プロジェクト削除", on_click=lambda e: open_confirm_delete_dialog()
    )

    def open_add_project_dialog():
        nonlocal add_project_dialog
        project_name_input.value = ""

        def on_add(e):
            nonlocal current_project, todos
            name = project_name_input.value.strip()
            if not name:
                return
            if name in settings["projects"]:
                page.open(ft.SnackBar(ft.Text("すでに存在します")))
                page.update()
                return
            settings["projects"].append(name)
            save_settings(settings)
            current_project = name
            set_last_project(current_project)
            update_project_dropdown()
            todos.clear()
            todos.extend(load_todos(current_project))
            update_todo_list()
            page.close(add_project_dialog)

        def on_cancel(e):
            page.close(add_project_dialog)

        add_project_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("プロジェクトの追加"),
            content=project_name_input,
            actions=[
                ft.ElevatedButton("追加", on_click=on_add),
                ft.TextButton("キャンセル", on_click=on_cancel),
            ],
            actions_alignment="end",
        )
        page.open(add_project_dialog)

    def open_confirm_delete_dialog():
        nonlocal confirm_delete_dialog

        def do_delete(e):
            nonlocal current_project, todos
            name = current_project
            if name == "Default":
                page.open(ft.SnackBar(ft.Text("Defaultは削除できません")))
                page.update()
                page.close(confirm_delete_dialog)
                return
            idx = settings["projects"].index(name)
            settings["projects"].remove(name)
            save_settings(settings)
            file = project_file(name)
            if os.path.exists(file):
                os.remove(file)
            if settings["projects"]:
                new_selection = settings["projects"][idx - 1] if idx > 0 else settings["projects"][0]
            else:
                new_selection = "Default"
                settings["projects"].append("Default")
                save_settings(settings)
            current_project = new_selection
            set_last_project(current_project)
            update_project_dropdown()
            todos.clear()
            todos.extend(load_todos(current_project))
            update_todo_list()
            page.close(confirm_delete_dialog)

        def on_cancel(e):
            page.close(confirm_delete_dialog)

        confirm_delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("削除確認"),
            content=ft.Text(f"「{current_project}」を削除しますか？"),
            actions=[
                ft.ElevatedButton("削除", on_click=do_delete),
                ft.TextButton("キャンセル", on_click=on_cancel),
            ],
            actions_alignment="end",
        )
        page.open(confirm_delete_dialog)

    add_todo_btn.on_click = on_add_todo
    update_todo_list()

    page.floating_action_button = fab

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        project_dropdown,
                        ft.Container(expand=True),
                        ft.Row(
                            [
                                add_project_btn,
                                del_project_btn,
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row([todo_input, add_todo_btn], spacing=8),
                ft.Container(
                    todo_list,
                    expand=True,
                    padding=8,
                ),
            ],
            expand=True,
            spacing=5,
        ),
    )


if __name__ == "__main__":
    import flet as ft

    ft.app(target=main)

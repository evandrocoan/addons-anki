from aqt import mw
from aqt.qt import *
from aqt.gui_hooks import editor_did_init_buttons
from aqt.editor import EditorMode, Editor
from aqt.browser import Browser
from anki.hooks import addHook
import os

from .settings_editor import SettingsWindow
from .process_notes import process_notes, generate_for_single_note
from .run_prompt_dialog import RunPromptDialog
from aqt import appVersion as aqt_version
from .__version__ import __version__ as plugin_version

import logging

ADDON_NAME = 'IntelliFiller'




def get_common_fields(selected_nodes_ids):
    common_fields = set(mw.col.getNote(selected_nodes_ids[0]).keys())
    for nid in selected_nodes_ids:
        note = mw.col.getNote(nid)
        note_fields = set(note.keys())
        common_fields = common_fields.intersection(note_fields)
    logging.debug("Common fields: %s", common_fields.join(","))
    return list(common_fields)


def create_run_prompt_dialog_from_browser(browser, prompt_config):
    common_fields = get_common_fields(browser.selectedNotes())
    dialog = RunPromptDialog(browser, common_fields, prompt_config)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        updated_prompt_config = dialog.get_result()
        process_notes(browser, updated_prompt_config)


def handle_browser_mode(editor: Editor, prompt_config):
    logging.debug("handling browser mode")
    browser: Browser = editor.parentWindow
    common_fields = get_common_fields(browser.selectedNotes())
    dialog = RunPromptDialog(browser, common_fields, prompt_config)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        updated_prompt_config = dialog.get_result()
        process_notes(browser, updated_prompt_config)


def handle_no_browser_mode(editor: Editor, prompt_config):
    """during edit current mode, the browser is not available, also the card does not yet have its own id."""
    logging.debug("handling NO browser mode")
    parentWindowOfEditor = editor.parentWindow
    logging.debug("parent window of editor: %s", parentWindowOfEditor)
    keys = editor.note.keys()
    dialog = RunPromptDialog(parentWindowOfEditor, keys, prompt_config)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        updated_prompt_config = dialog.get_result()
        generate_for_single_note(editor, updated_prompt_config)


def create_run_prompt_dialog_from_editor(editor: Editor, prompt_config):
    if editor.editorMode == EditorMode.BROWSER:
        handle_browser_mode(editor, prompt_config)
    elif editor.editorMode == EditorMode.EDIT_CURRENT or editor.editorMode == EditorMode.ADD_CARDS:
        handle_no_browser_mode(editor, prompt_config)


def add_context_menu_items(browser, menu):
    submenu = QMenu(ADDON_NAME, menu)
    menu.addMenu(submenu)
    config = mw.addonManager.getConfig(__name__)

    for prompt_config in config['prompts']:
        action = QAction(prompt_config["promptName"], browser)
        action.triggered.connect(lambda _, br=browser, pc=prompt_config: create_run_prompt_dialog_from_browser(br, pc))
        submenu.addAction(action)


def open_settings():
    window = SettingsWindow(mw)
    window.exec()


def on_editor_button(editor):
    prompts = mw.addonManager.getConfig(__name__).get('prompts', [])

    menu = QMenu(editor.widget)
    for i, prompt in enumerate(prompts):
        action = QAction(f'Prompt {i + 1}: {prompt["promptName"]}', menu)
        action.triggered.connect(lambda _, p=prompt: create_run_prompt_dialog_from_editor(editor, p))
        menu.addAction(action)

    menu.exec(editor.widget.mapToGlobal(QPoint(0, 0)))
    logging.debug("Editor button is pressed")


def on_setup_editor_buttons(buttons, editor):
    icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
    btn = editor.addButton(
        icon=icon_path,
        cmd="run_prompt",
        func=lambda e=editor: on_editor_button(e),
        tip=ADDON_NAME,
        keys=None,
        disables=False
    )
    buttons.append(btn)
    logging.debug("Editor buttons are set up")
    return buttons


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s in %(filename)s:%(lineno)d',
                    datefmt='%Y-%m-%d %H:%M:%S')

logging.info('Python version: ' + sys.version)
logging.info('Anki version: ' + aqt_version)
logging.info('IntelliFilter version: ' + plugin_version)
logging.info('Environment variables:')
for key, value in os.environ.items():
    logging.info(f'{key}: {value}')

addHook("browser.onContextMenu", add_context_menu_items)
mw.addonManager.setConfigAction(__name__, open_settings)
editor_did_init_buttons.append(on_setup_editor_buttons)

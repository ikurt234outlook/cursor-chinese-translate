# -*- coding: utf-8 -*-
"""
菜单模块 - 提供交互式菜单界面
"""

import os
import platform
import sys

CURRENT_PLATFORM = platform.system().lower()

# 平台显示名称映射（仅用于输出，不改变内部逻辑）
PLATFORM_DISPLAY_NAMES = {
    'windows': 'win',
    'darwin': 'macos',
    'linux': 'linux',
}


def get_platform_display_name():
    """获取平台显示名称"""
    return PLATFORM_DISPLAY_NAMES.get(CURRENT_PLATFORM, CURRENT_PLATFORM)


def get_default_cursor_install_path():
    """获取默认的 Cursor 安装路径（区分 win/mac/linux）"""
    if CURRENT_PLATFORM == 'windows':
        return os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Programs", "cursor"
        )
    elif CURRENT_PLATFORM == 'darwin':  # macOS
        return "/Applications/Cursor.app/Contents/Resources/app"
    elif CURRENT_PLATFORM == 'linux':
        return "/usr/share/cursor"
    else:
        return "/usr/share/cursor"


def get_default_cursor_user_data_path():
    """获取默认的 Cursor 用户数据路径（区分 win/mac/linux）"""
    if CURRENT_PLATFORM == 'windows':
        return os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Cursor"
        )
    elif CURRENT_PLATFORM == 'darwin':  # macOS
        return os.path.expanduser("~/Library/Application Support/Cursor")
    elif CURRENT_PLATFORM == 'linux':
        return os.path.expanduser("~/.cursor")
    else:
        return os.path.expanduser("~/.cursor")


def auto_detect_cursor_install_path():
    """自动检测 Cursor 安装路径"""
    default_path = get_default_cursor_install_path()
    if os.path.exists(default_path):
        # macOS 的 app 路径结构不同
        if CURRENT_PLATFORM == 'darwin':
            if os.path.exists(os.path.join(default_path, "out", "vs", "code", "electron-sandbox", "workbench")):
                return default_path
        else:
            if os.path.exists(os.path.join(default_path, "resources", "app")):
                return default_path

    # 尝试其他常见路径
    if CURRENT_PLATFORM == 'darwin':
        common_paths = [
            "/Applications/Cursor.app/Contents/Resources/app",
            os.path.expanduser("~/Applications/Cursor.app/Contents/Resources/app"),
        ]
    elif CURRENT_PLATFORM == 'windows':
        common_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Cursor", "resources", "app"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Cursor", "resources", "app"),
        ]
    else:  # linux
        common_paths = [
            "/usr/share/cursor",
            "/opt/cursor",
            "/usr/local/share/cursor",
        ]

    for path in common_paths:
        if os.path.exists(path):
            if CURRENT_PLATFORM == 'darwin':
                if os.path.exists(os.path.join(path, "out", "vs", "code", "electron-sandbox", "workbench")):
                    return path
            else:
                if os.path.exists(os.path.join(path, "resources", "app")):
                    return path

    return None


def auto_detect_cursor_user_data_path():
    """自动检测 Cursor 用户数据路径"""
    default_path = get_default_cursor_user_data_path()
    if os.path.exists(default_path):
        return default_path

    # 尝试其他常见路径
    if CURRENT_PLATFORM == 'darwin':
        common_paths = [
            os.path.expanduser("~/Library/Application Support/Cursor"),
            os.path.expanduser("~/.cursor"),
        ]
    elif CURRENT_PLATFORM == 'windows':
        common_paths = [
            os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Cursor"),
            os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Cursor"),
        ]
    else:  # linux
        common_paths = [
            os.path.expanduser("~/.cursor"),
        ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def display_menu():
    """显示主菜单"""
    print("\n" + "=" * 60)
    print("  Cursor 汉化 + 用量监控工具")
    print(f"  平台: {get_platform_display_name()}")
    print("=" * 60)
    print("\n请选择操作：")
    print("  1. 安装汉化")
    print("  2. 卸载汉化")
    print("  3. 安装用量监控")
    print("  4. 卸载用量监控")
    print("  0. 退出")
    print("\n" + "-" * 60)


def get_user_choice():
    """获取用户选择"""
    while True:
        try:
            choice = input("\n请输入选项编号 (0-4): ").strip()
            if choice in ['0', '1', '2', '3', '4']:
                return choice
            print("[错误] 无效的选项，请输入 0-4 之间的数字")
        except KeyboardInterrupt:
            print("\n\n[退出] 用户中断")
            sys.exit(0)
        except EOFError:
            print("\n\n[退出] 输入结束")
            sys.exit(0)


def get_cursor_install_path(custom_path=None):
    """获取 Cursor 安装路径"""
    if custom_path:
        if os.path.exists(custom_path):
            return custom_path
        else:
            print(f"[错误] 指定的路径不存在: {custom_path}")
            return None

    # 自动检测
    detected_path = auto_detect_cursor_install_path()
    if detected_path:
        print(f"[检测] 自动识别 Cursor 安装路径: {detected_path}")
        return detected_path

    # 提示用户输入
    print("[提示] 未能自动识别 Cursor 安装路径")
    print(f"[提示] 默认路径: {get_default_cursor_install_path()}")

    while True:
        try:
            user_input = input("请输入 Cursor 安装路径（或按回车使用默认路径）: ").strip()
            if not user_input:
                return get_default_cursor_install_path()

            if os.path.exists(user_input):
                return user_input
            else:
                print(f"[错误] 路径不存在: {user_input}")
                retry = input("是否重试？(y/n): ").strip().lower()
                if retry != 'y':
                    return None
        except KeyboardInterrupt:
            print("\n\n[退出] 用户中断")
            sys.exit(0)
        except EOFError:
            print("\n\n[退出] 输入结束")
            sys.exit(0)


def confirm_action(action_name):
    """确认操作"""
    while True:
        try:
            response = input(f"\n确认执行 {action_name}？(y/n): ").strip().lower()
            if response in ['y', 'yes', '是', '确认']:
                return True
            if response in ['n', 'no', '否', '取消']:
                return False
            print("[提示] 请输入 y/是 或 n/否")
        except KeyboardInterrupt:
            print("\n\n[退出] 用户中断")
            sys.exit(0)
        except EOFError:
            print("\n\n[退出] 输入结束")
            sys.exit(0)


def run_interactive_menu(cursor_install_path=None):
    """运行交互式菜单"""
    from translator import install_translation, uninstall_translation, update_checksum
    from usage_monitor import install_usage_monitor, uninstall_usage_monitor

    while True:
        display_menu()
        choice = get_user_choice()

        if choice == '0':
            print("\n[退出] 感谢使用，再见！")
            break

        # 获取 Cursor 安装路径
        if cursor_install_path is None:
            cursor_install_path = get_cursor_install_path()
            if cursor_install_path is None:
                print("[错误] 无法确定 Cursor 安装路径")
                continue

        if choice == '1':
            # 安装汉化
            if confirm_action("安装汉化"):
                success = install_translation(cursor_install_path)
                if success:
                    update_checksum(cursor_install_path)
                    print("\n[完成] 汉化安装成功！请重启 Cursor。")

        elif choice == '2':
            # 卸载汉化
            if confirm_action("卸载汉化"):
                success = uninstall_translation(cursor_install_path)
                if success:
                    update_checksum(cursor_install_path)
                    print("\n[完成] 汉化卸载成功！")

        elif choice == '3':
            # 安装用量监控
            if confirm_action("安装用量监控"):
                success = install_usage_monitor(cursor_install_path)
                if success:
                    update_checksum(cursor_install_path)
                    print("\n[完成] 用量监控安装成功！请重启 Cursor。")

        elif choice == '4':
            # 卸载用量监控
            if confirm_action("卸载用量监控"):
                success = uninstall_usage_monitor(cursor_install_path)
                if success:
                    update_checksum(cursor_install_path)
                    print("\n[完成] 用量监控卸载成功！")


def is_interactive():
    """检测是否在交互式终端中运行"""
    return sys.stdin.isatty()

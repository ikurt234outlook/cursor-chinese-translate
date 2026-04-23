# -*- coding: utf-8 -*-
"""
Cursor 汉化 + 用量监控工具
功能：
  1. 将翻译脚本注入 Cursor 的 workbench.html，实现设置页面中文化
  2. 自动从本地数据库读取认证令牌，调用 API 获取用量数据
  3. 在 Cursor 设置页面用户信息区域下方显示实时用量情况

用法：
  python CursorTranslate.py --install-translation    安装汉化
  python CursorTranslate.py --uninstall-translation  卸载汉化
  python CursorTranslate.py --install-usage          安装用量监控
  python CursorTranslate.py --uninstall-usage        卸载用量监控
  python CursorTranslate.py --menu                   交互式菜单
  python CursorTranslate.py                          交互式菜单（自动检测）
"""

import argparse
import datetime
import os
import platform
import sys

# 添加当前目录到模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translator import (
    install_translation,
    uninstall_translation,
    update_checksum,
    auto_detect_cursor_install_path,
)
from usage_monitor import (
    install_usage_monitor,
    uninstall_usage_monitor,
    auto_detect_cursor_user_data_path,
)
from menu import run_interactive_menu, is_interactive, get_default_cursor_install_path

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


DEFAULT_CURSOR_INSTALL_PATH = get_default_cursor_install_path()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Cursor 汉化 + 用量监控工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python CursorTranslate.py --install-translation    安装汉化
  python CursorTranslate.py --uninstall-translation  卸载汉化
  python CursorTranslate.py --install-usage          安装用量监控
  python CursorTranslate.py --uninstall-usage        卸载用量监控
  python CursorTranslate.py --menu                   交互式菜单
  python CursorTranslate.py                          交互式菜单（自动检测）
        """
    )

    parser.add_argument('--install-translation', action='store_true',
                        help='安装汉化')
    parser.add_argument('--uninstall-translation', action='store_true',
                        help='卸载汉化')
    parser.add_argument('--install-usage', action='store_true',
                        help='安装用量监控')
    parser.add_argument('--uninstall-usage', action='store_true',
                        help='卸载用量监控')
    parser.add_argument('--menu', action='store_true',
                        help='进入交互式菜单')
    parser.add_argument('--cursorDir', dest='cursor_dir',
                        help='指定 Cursor 安装目录')

    args = parser.parse_args()

    # 验证参数组合
    action_count = sum([
        args.install_translation,
        args.uninstall_translation,
        args.install_usage,
        args.uninstall_usage,
    ])

    if action_count > 1:
        print("[错误] 不能同时指定多个操作")
        sys.exit(1)

    return args


def resolve_cursor_install_path(cursor_dir=None):
    """解析 Cursor 安装路径（自动识别或使用指定路径）"""
    if cursor_dir:
        if os.path.exists(cursor_dir):
            return cursor_dir
        else:
            print(f"[错误] 指定的路径不存在: {cursor_dir}")
            return None

    # 自动检测
    detected_path = auto_detect_cursor_install_path()
    if detected_path:
        print(f"[检测] 自动识别 Cursor 安装路径: {detected_path}")
        return detected_path

    print("[错误] 未能自动识别 Cursor 安装路径")
    print(f"[提示] 默认路径: {DEFAULT_CURSOR_INSTALL_PATH}")
    print("[提示] 请使用 --cursorDir 指定安装路径")
    return None


def print_help():
    """打印帮助信息"""
    print("=" * 60)
    print("  Cursor 汉化 + 用量监控工具")
    print(f"  平台: {get_platform_display_name()}")
    print("=" * 60)
    print("\n用法：")
    print("  python CursorTranslate.py --install-translation    安装汉化")
    print("  python CursorTranslate.py --uninstall-translation  卸载汉化")
    print("  python CursorTranslate.py --install-usage          安装用量监控")
    print("  python CursorTranslate.py --uninstall-usage        卸载用量监控")
    print("  python CursorTranslate.py --menu                   交互式菜单")
    print("  python CursorTranslate.py                          交互式菜单（自动检测）")
    print(f"\n默认安装目录: {DEFAULT_CURSOR_INSTALL_PATH}")
    print("如需指定其他路径，请使用 --cursorDir=\"路径\"")


def main():
    """主程序入口"""
    args = parse_arguments()

    # 如果没有参数或指定了 --menu，进入交互式菜单
    if len(sys.argv) == 1 or args.menu:
        if is_interactive():
            run_interactive_menu(args.cursor_dir)
            return
        else:
            print_help()
            return

    # 命令行模式：解析安装路径
    cursor_install_path = resolve_cursor_install_path(args.cursor_dir)
    if cursor_install_path is None:
        sys.exit(1)

    print("=" * 60)
    print("  Cursor 汉化 + 用量监控工具")
    print(f"  平台: {get_platform_display_name()}")
    print(f"  时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.install_translation:
        success = install_translation(cursor_install_path)
        if success:
            update_checksum(cursor_install_path)
            print("\n[完成] 汉化安装成功！请重启 Cursor。")

    elif args.uninstall_translation:
        success = uninstall_translation(cursor_install_path)
        if success:
            update_checksum(cursor_install_path)
            print("\n[完成] 汉化卸载成功！")

    elif args.install_usage:
        success = install_usage_monitor(cursor_install_path)
        if success:
            update_checksum(cursor_install_path)
            print("\n[完成] 用量监控安装成功！请重启 Cursor。")

    elif args.uninstall_usage:
        success = uninstall_usage_monitor(cursor_install_path)
        if success:
            update_checksum(cursor_install_path)
            print("\n[完成] 用量监控卸载成功！")

    else:
        print_help()


if __name__ == '__main__':
    main()

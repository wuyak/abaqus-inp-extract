#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量提取调度器

读取 elsets.py 配置，循环调用 scripts/extract.py 进行提取

用法：
    python batch.py [source.inp]

示例：
    python batch.py                      # 使用默认 silverado/silverado.inp
    python batch.py f150/model.inp       # 指定 INP 文件路径
"""
import subprocess
import sys
import os
import argparse


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='从 ABAQUS INP 文件中批量提取预定义的待提取系统',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'source_inp',
        nargs='?',
        default='silverado/silverado.inp',
        help='源 INP 文件路径 (默认: silverado/silverado.inp)'
    )

    args = parser.parse_args()

    # 检查源文件是否存在
    if not os.path.exists(args.source_inp):
        print(f"错误: 未找到源文件 {args.source_inp}")
        return 1

    # 获取源文件所在目录和基础名称
    source_dir = os.path.dirname(os.path.abspath(args.source_inp))
    source_basename = os.path.splitext(os.path.basename(args.source_inp))[0]

    # 检查同目录下是否有 elsets.py
    elsets_file = os.path.join(source_dir, 'elsets.py')
    if not os.path.exists(elsets_file):
        print(f"错误: 未找到 {elsets_file}")
        print(f"请在 {source_dir}/ 目录创建 elsets.py，定义 SYSTEMS 字典")
        return 1

    # 导入 ELSET 分组配置
    sys.path.insert(0, source_dir)
    try:
        from elsets import SYSTEMS
    except ImportError as e:
        print(f"错误: 无法导入 {elsets_file}: {e}")
        return 1

    print(f"[批量提取] {source_basename.upper()}")
    print(f"[源文件] {args.source_inp}")
    print(f"[配置文件] {elsets_file}")
    print("-" * 40)
    for name, elsets in SYSTEMS.items():
        print(f"  {name:20} {len(elsets):>3} 个部件")
    print("-" * 40)

    # 批量提取各系统
    print()
    output_prefix = source_basename
    for system_name, elset_list in SYSTEMS.items():
        if not elset_list:
            print(f"[{system_name}] 跳过 (无部件)")
            continue

        print(f"[{system_name}] 提取中...")

        # 输出文件与源文件在同一目录
        output_file = os.path.join(source_dir, f'{output_prefix}_{system_name}.inp')
        elsets_str = ','.join(elset_list)

        # 调用 scripts/extract.py
        cmd = [
            sys.executable, 'scripts/extract.py',
            args.source_inp,
            '--elsets', elsets_str,
            '-o', output_file
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # 只显示关键信息
                for line in result.stdout.split('\n'):
                    if line.startswith('['):
                        print(f"  {line}")
            else:
                print(f"  [失败] 错误代码 {result.returncode}")
                if result.stderr:
                    print(f"  {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            print(f"  [超时] 处理超过5分钟")
        except Exception as e:
            print(f"  [错误] {e}")

    print("\n[完成] 批量提取完成")
    return 0


if __name__ == '__main__':
    sys.exit(main())

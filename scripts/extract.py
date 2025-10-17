#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABAQUS INP文件ELSET提取工具

功能：从大型INP文件中提取指定ELSET的完整模型
输出：包含节点、单元、材料、截面、耦合约束的新INP文件

用法：
    python extract.py source.inp --elsets ELSET1,ELSET2,ELSET3 -o output.inp
"""
import argparse
import sys
import os
import pickle
from parse import parse_inp_file
from extractor import extract_complete_model


def load_or_parse(source_inp, parse_func):
    """加载缓存或重新解析INP文件"""
    cache_file = source_inp + '.cache.pkl'

    # 检查缓存是否有效
    if os.path.exists(cache_file):
        try:
            cache_mtime = os.path.getmtime(cache_file)
            source_mtime = os.path.getmtime(source_inp)

            if cache_mtime > source_mtime:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, dict) and 'elements' in data and 'nodes' in data:
                        return data
        except:
            pass

    # 重新解析
    parsed_data = parse_func(source_inp)

    # 保存缓存
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(parsed_data, f)
    except:
        pass

    return parsed_data


def main():
    parser = argparse.ArgumentParser(
        description='从ABAQUS INP文件中提取指定ELSET的完整模型',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python extract_inp.py model.inp --elsets wheel-hub,wheel-tyre -o wheels.inp
  python extract_inp.py model.inp --elsets PART1 -o output.inp --no-cache
        """
    )

    parser.add_argument('input',
                       help='源INP文件路径')

    parser.add_argument('--elsets', required=True,
                       help='目标ELSET名称（逗号分隔，例如: ELSET1,ELSET2,ELSET3）')

    parser.add_argument('-o', '--output', required=True,
                       help='输出INP文件路径')

    parser.add_argument('--no-cache', action='store_true',
                       help='强制重新解析（忽略缓存）')

    args = parser.parse_args()

    # 解析ELSET列表
    target_elsets = [s.strip() for s in args.elsets.split(',') if s.strip()]
    if not target_elsets:
        print("错误: 未指定有效的ELSET")
        return 1

    try:
        # 显示目标ELSET（简化）
        if len(target_elsets) <= 3:
            print(f"[目标] {', '.join(target_elsets)}")
        else:
            print(f"[目标] {len(target_elsets)}个ELSET: {', '.join(target_elsets[:3])}, ...")

        # 解析（使用缓存）
        if args.no_cache:
            parsed_data = parse_inp_file(args.input)
        else:
            parsed_data = load_or_parse(args.input, parse_inp_file)

        # 提取
        extract_complete_model(parsed_data, target_elsets, args.output, args.input)

        return 0

    except FileNotFoundError as e:
        print(f"\n错误: 文件未找到 - {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n用户中断")
        return 1
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

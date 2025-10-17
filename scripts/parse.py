#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABAQUS INP文件解析器
"""


# ============================================================================
# 块路由配置（Block Routing Configuration）
# ============================================================================
# 每个关键词的存储策略：(目标字典名, 索引键名, 操作类型)
# 操作类型：'index' = 按键索引存储, 'append' = 追加到列表

BLOCK_ROUTING = {
    # 几何和拓扑
    'element': ('elements', 'elset', 'index'),
    'nset': ('nsets', 'nset', 'index'),
    'elset': ('elsets', 'elset', 'index'),

    # 材料和截面
    'material': ('materials', 'name', 'index'),
    'solid section': ('sections', 'elset', 'index'),
    'shell section': ('sections', 'elset', 'index'),
    'beam section': ('sections', 'elset', 'index'),
    'connector section': ('sections', 'elset', 'index'),
    'membrane section': ('sections', 'elset', 'index'),
    'surface section': ('sections', 'elset', 'index'),
    'cohesive section': ('sections', 'elset', 'index'),
    'gasket section': ('sections', 'elset', 'index'),
    'truss section': ('sections', 'elset', 'index'),
    'frame section': ('sections', 'elset', 'index'),

    # 连接器
    'connector behavior': ('connector_behaviors', 'name', 'index'),

    # 约束（所有约束类型统一追加到列表）
    'coupling': ('constraints', None, 'append'),
    'kinematic': ('constraints', None, 'append'),
    'distributing': ('constraints', None, 'append'),
    'rigid body': ('constraints', None, 'append'),
    'mpc': ('constraints', None, 'append'),
    'tie': ('constraints', None, 'append'),
    'equation': ('constraints', None, 'append'),
    'embedded region': ('constraints', None, 'append'),
    'shell to solid coupling': ('constraints', None, 'append'),
    'cyclic symmetry model': ('constraints', None, 'append'),
}


def parse_keyword_line(line):
    """
    解析关键字行，提取关键字名称和参数

    示例：
        *Material, Name=STEEL  → ('material', {'name': 'STEEL'})
        *Element, Type=C3D8R, Elset=wheel → ('element', {'type': 'C3D8R', 'elset': 'wheel'})
    """
    line = line.strip()
    if not line.startswith('*') or line.startswith('**'):
        return None, {}

    # 分割token
    tokens = [t.strip() for t in line[1:].split(",") if t.strip()]
    if not tokens:
        return None, {}

    keyword = tokens[0].lower()

    # 解析参数
    options = {}
    for token in tokens[1:]:
        if '=' in token:
            key, value = token.split('=', 1)
            options[key.strip().lower()] = value.strip()

    return keyword, options


class Block:
    """INP文件中的一个块（关键字 + 完整内容）"""

    def __init__(self, keyword, options, lines):
        self.keyword = keyword      # 'material', 'element', 'section', etc.
        self.options = options      # {'name': 'STEEL', 'elset': 'wheel'}
        self.lines = lines          # 完整的块内容（包括关键字行和数据行）
        self.nodes = None           # 仅用于 ELEMENT 块，存储节点ID集合

    def __repr__(self):
        return f"Block(keyword='{self.keyword}', options={self.options}, lines={len(self.lines)})"


def _save_node_block(result, lines):
    """保存 NODE 块到 nodes 字典"""
    for line in lines[1:]:  # 跳过关键字行
        if not line.strip() or line.strip().startswith('**') or line.startswith('*'):
            continue
        try:
            node_id = int(line.split(',')[0].strip())
            result['nodes'][node_id] = line
        except (ValueError, IndexError):
            continue


def _save_block(result, keyword, options, lines):
    """保存块到对应的分类（数据驱动路由）"""

    block = Block(keyword, options, lines)

    # 查找路由规则
    if keyword not in BLOCK_ROUTING:
        # 未定义的关键字（包括NODE），放到others
        result['others'].append(block)
        return

    target_dict, index_key, operation = BLOCK_ROUTING[keyword]

    # 特殊处理：ELEMENT块附加节点ID集合
    if keyword == 'element':
        nodes = set()
        for line in block.lines[1:]:
            if not line.strip() or line.strip().startswith(('**', '*')):
                continue
            try:
                parts = line.split(',')
                # 跳过第一个（单元ID），后面都是节点ID
                for part in parts[1:]:
                    node_id = int(part.strip())
                    nodes.add(node_id)
            except (ValueError, IndexError):
                continue
        block.nodes = nodes

    # 根据操作类型执行存储
    if operation == 'append':
        result[target_dict].append(block)
    elif operation == 'index':
        key_value = options.get(index_key, '').lower()
        if key_value:
            result[target_dict][key_value] = block


def parse_inp_file(inp_file):
    """
    解析INP文件，返回按类型分组的块列表

    Returns:
        dict: {
            'nodes': {node_id: line_string},
            'elements': {elset_name: Block},
            'materials': {material_name: Block},
            'sections': {elset_name: Block},
            'constraints': [Block, Block, ...],
            'nsets': {nset_name: Block},
            'elsets': {elset_name: Block},
            'connector_behaviors': {behavior_name: Block},
            'others': [Block, ...]
        }
    """

    result = {
        'nodes': {},
        'elements': {},
        'materials': {},
        'sections': {},
        'constraints': [],
        'nsets': {},
        'elsets': {},
        'connector_behaviors': {},
        'others': []
    }

    current_keyword = None
    current_options = {}
    current_lines = []

    with open(inp_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip()

            # 跳过注释行和空行
            if not line.strip() or line.strip().startswith('**'):
                if current_keyword:
                    current_lines.append(line)
                continue

            # 检查是否是关键字行
            if line.startswith('*'):
                keyword, options = parse_keyword_line(line)

                # 特殊处理：NODE 块
                if keyword == 'node':
                    # 保存上一个块
                    if current_keyword == 'node':
                        _save_node_block(result, current_lines)
                    elif current_keyword:
                        _save_block(result, current_keyword, current_options, current_lines)

                    # 开始新 NODE 块
                    current_keyword = 'node'
                    current_options = options
                    current_lines = [line]
                    continue

                # 判断是否是主关键字（会开始新块）
                if keyword and keyword in BLOCK_ROUTING:
                    # 保存上一个块
                    if current_keyword == 'node':
                        _save_node_block(result, current_lines)
                    elif current_keyword:
                        _save_block(result, current_keyword, current_options, current_lines)

                    # 开始新块
                    current_keyword = keyword
                    current_options = options
                    current_lines = [line]
                    continue

            # 累积当前块的内容
            if current_keyword:
                current_lines.append(line)

        # 保存最后一个块
        if current_keyword == 'node':
            _save_node_block(result, current_lines)
        elif current_keyword:
            _save_block(result, current_keyword, current_options, current_lines)

    return result

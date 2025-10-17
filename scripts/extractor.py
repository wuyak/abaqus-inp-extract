#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INP文件提取器

提取指定ELSET及其完整依赖（节点、材料、截面、约束）
"""


# ============================================================================
# 辅助函数
# ============================================================================

def _get_nodes_from_data_lines(lines):
    """从数据行中解析节点ID集合（跳过关键字行和注释）"""
    nodes = set()
    for line in lines[1:]:  # 跳过关键字行
        if not line.strip() or line.strip().startswith('**'):
            continue
        for part in line.split(','):
            if part.strip().isdigit():
                nodes.add(int(part.strip()))
    return nodes


# ============================================================================
# 约束筛选逻辑
# ============================================================================

def _validate_constraint(block, all_nodes, target_elsets):
    """
    判断约束是否与目标模型相关

    相关条件（满足任一即可）：
    1. 引用的 ref node 在目标节点集内
    2. 引用的 elset 在目标ELSET集内
    3. 数据行中的节点在目标节点集内
    """
    # 检查 ref node
    ref_node = block.options.get('ref node', '')
    if ref_node.isdigit() and int(ref_node) in all_nodes:
        return True

    # 检查 elset
    elset = block.options.get('elset', '').lower()
    if elset in target_elsets:
        return True

    # 检查数据行中的节点
    nodes_in_data = _get_nodes_from_data_lines(block.lines)
    if any(node in all_nodes for node in nodes_in_data):
        return True

    return False


def _collect_constraint_dependencies(block, parsed_data, required_nsets, required_elsets, all_nodes):
    """收集约束引用的依赖（nset, elset, 节点）"""
    # 收集 ref node
    ref_node = block.options.get('ref node', '')
    if ref_node.isdigit():
        all_nodes.add(int(ref_node))

    # 收集数据行中的所有节点
    all_nodes.update(_get_nodes_from_data_lines(block.lines))

    # 收集 nset 依赖及其节点
    for key in ['ref node', 'tie nset', 'nset']:
        nset_name = block.options.get(key, '').lower()
        if nset_name and nset_name in parsed_data['nsets']:
            required_nsets.add(nset_name)
            nset_block = parsed_data['nsets'][nset_name]
            all_nodes.update(_get_nodes_from_data_lines(nset_block.lines))

    # 收集 elset 依赖
    elset_name = block.options.get('elset', '').lower()
    if elset_name and elset_name in parsed_data['elsets']:
        required_elsets.add(elset_name)


# ============================================================================
# 主提取逻辑
# ============================================================================

def extract_complete_model(parsed_data, target_elsets, output_file, source_file=None):
    """
    从解析数据中提取完整模型（节点、单元、耦合、Section、材料）

    Args:
        parsed_data: parse_inp_file()返回的数据（Block结构）
        target_elsets: 目标ELSET列表
        output_file: 输出INP文件路径
        source_file: 源文件名（用于输出文件头部注释）
    """
    target_elsets_lower = {e.lower() for e in target_elsets}

    # ========================================================================
    # 1. 收集目标ELSET的单元和节点
    # ========================================================================
    target_element_blocks = {}
    all_nodes_needed = set()

    for elset_lower, block in parsed_data['elements'].items():
        if elset_lower in target_elsets_lower:
            target_element_blocks[elset_lower] = block
            all_nodes_needed.update(block.nodes)

    total_elements = sum(len([l for l in b.lines[1:] if l.strip() and not l.startswith('**') and not l.startswith('*')])
                        for b in target_element_blocks.values())
    print(f"[单元] {total_elements}个单元, {len(all_nodes_needed)}个节点")

    # ========================================================================
    # 2. 筛选约束并收集依赖
    # ========================================================================
    valid_constraints = []
    required_nsets = set()
    required_elsets = set()

    for block in parsed_data['constraints']:
        if _validate_constraint(block, all_nodes_needed, target_elsets_lower):
            valid_constraints.append(block)
            _collect_constraint_dependencies(block, parsed_data, required_nsets, required_elsets, all_nodes_needed)

    if valid_constraints or required_nsets or required_elsets:
        info_parts = []
        if valid_constraints:
            info_parts.append(f"{len(valid_constraints)}个约束")
        if required_nsets:
            info_parts.append(f"{len(required_nsets)}个Nset")
        if required_elsets:
            info_parts.append(f"{len(required_elsets)}个Elset")
        print(f"[约束] {', '.join(info_parts)}")

    # ========================================================================
    # 3. 提取截面和材料
    # ========================================================================
    target_section_blocks = {}
    referenced_materials = set()
    referenced_behaviors = set()

    # 筛选目标ELSET的截面
    for elset_lower, block in parsed_data['sections'].items():
        if elset_lower in target_elsets_lower:
            target_section_blocks[elset_lower] = block
            # 收集材料名称
            mat_name = block.options.get('material', '').strip()
            if mat_name:
                referenced_materials.add(mat_name.lower())
            # 收集Connector Behavior名称
            behavior_name = block.options.get('behavior', '').strip()
            if behavior_name:
                referenced_behaviors.add(behavior_name.lower())

    # 筛选被引用的材料和行为
    target_material_blocks = {name: block for name, block in parsed_data['materials'].items()
                             if name in referenced_materials}
    target_behavior_blocks = {name: block for name, block in parsed_data['connector_behaviors'].items()
                             if name in referenced_behaviors}

    if target_section_blocks or target_material_blocks or target_behavior_blocks:
        info_parts = []
        if target_section_blocks:
            info_parts.append(f"{len(target_section_blocks)}个截面")
        if target_material_blocks:
            info_parts.append(f"{len(target_material_blocks)}个材料")
        if target_behavior_blocks:
            info_parts.append(f"{len(target_behavior_blocks)}个Behavior")
        print(f"[属性] {', '.join(info_parts)}")

    # ========================================================================
    # 4. 写入输出文件
    # ========================================================================
    _write_output_file(
        output_file, source_file, target_elsets, parsed_data, all_nodes_needed,
        target_element_blocks, target_section_blocks, target_material_blocks,
        target_behavior_blocks, valid_constraints, required_nsets, required_elsets
    )


def _write_output_file(output_file, source_file, target_elsets, parsed_data, nodes_needed,
                       element_blocks, section_blocks, material_blocks, behavior_blocks,
                       constraints, required_nsets, required_elsets):
    """写入输出INP文件（按原文件顺序保持拓扑正确性）"""

    with open(output_file, 'w', encoding='utf-8') as f:
        # ABAQUS标准头部
        f.write("*HEADING\n")
        f.write(f"Extracted model - ELSETs: {', '.join(target_elsets[:3])}")
        if len(target_elsets) > 3:
            f.write(f" and {len(target_elsets) - 3} more")
        f.write("\n")
        if source_file:
            f.write(f"** Source: {source_file}\n")
        f.write("**\n")

        # 写入节点
        f.write("*NODE\n")
        for node_id in sorted(nodes_needed):
            if node_id in parsed_data['nodes']:
                f.write(parsed_data['nodes'][node_id] + '\n')

        # 写入单元（按element类型分组）
        for elset_name, block in element_blocks.items():
            elem_type = block.options.get('type', 'UNKNOWN')
            f.write(f'*Element, Type={elem_type}, Elset={elset_name}\n')
            for line in block.lines[1:]:
                if line.strip() and not line.strip().startswith('**') and not line.startswith('*'):
                    f.write(line + '\n')

        # 写入Nset定义（按原文件顺序，自然保持拓扑序）
        if required_nsets:
            for nset_name, block in parsed_data['nsets'].items():
                if nset_name in required_nsets:
                    for line in block.lines:
                        if not line.strip().startswith('**'):
                            f.write(line + '\n')

        # 写入Elset定义（按原文件顺序）
        if required_elsets:
            for elset_name, block in parsed_data['elsets'].items():
                if elset_name in required_elsets:
                    for line in block.lines:
                        if not line.strip().startswith('**'):
                            f.write(line + '\n')

        # 写入Section（在约束之前）
        if section_blocks:
            for elset_name, block in section_blocks.items():
                for line in block.lines:
                    if not line.strip().startswith('**'):
                        f.write(line + '\n')

        # 写入材料（在约束之前）
        if material_blocks:
            for mat_name, block in material_blocks.items():
                for line in block.lines:
                    if not line.strip().startswith('**'):
                        f.write(line + '\n')

        # 写入Connector Behavior（在Section之后，约束之前）
        if behavior_blocks:
            for behavior_name, block in behavior_blocks.items():
                for line in block.lines:
                    if not line.strip().startswith('**'):
                        f.write(line + '\n')

        # 写入约束（放在最后，符合ABAQUS标准，保留注释以显示约束名称）
        if constraints:
            for block in constraints:
                for line in block.lines:
                    f.write(line + '\n')

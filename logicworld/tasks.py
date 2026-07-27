"""Task generation utilities for LOGICWorld."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from logicworld.config import ITEM_ATTRIBUTES, RECEPTACLE_TO_ITEMS as receptacle2ITEMS

if TYPE_CHECKING:
    from logicworld.env import LOGICWorldEnv


class TaskGenerator:
    """Generate basic / advanced / logic-conditioned tasks for an environment.

    Methods proxy environment state via ``self.env`` (also available through
    attribute fallback), so existing task logic can keep using ``self.items``,
    ``self.get_item_count``, verification helpers, etc.
    """

    def __init__(self, env: "LOGICWorldEnv"):
        self.env = env

    def __getattr__(self, name: str) -> Any:
        # Delegate state / helpers to the owning environment.
        return getattr(self.env, name)

    # Basic tasks ------------------------------------------------------------------------------------- #
    def create_visited_item_task(self, type=1):
        if type==1:
            # 1. 获取所有可访问的物品（精确名称）
            precise_item_list = [item for item in self.items if self.items[item].level >1]
            
            if not precise_item_list:
                return "No accessible items.", ""

            target_item = random.choice(precise_item_list)
            # task = f"搜索{target_item}并导航到它面前。"
            task = f"Search for the {target_item} and navigate to its front."
            verify = f"self.located('{target_item}')"
        
        elif type==2:
            # 获取所有可访问的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "No accessible items.", ""

            target_item = random.choice(blurred_item_list)
            # task = f"导航到任意一个{target_item}面前。"
            task = f"Search for any one {target_item} and navigate to its front."
            verify = f"self.located('{target_item}')"
        elif type==-1:
            # miss
            out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
            out_receptacles = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['placeable']]
            target_item = random.choice(out_items+out_receptacles)
            task = f"Search for any one {target_item} and navigate to its front."
            reason = f"{target_item} not exist!"
            return task, reason
        else:
            return '', ''
        
        return task, verify

    def create_pickup_item_task(self, type=1):
        
        if type==1:
            # 1. 获取所有可拿取的物品（精确名称）
            precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
            
            if not precise_item_list:
                return "There are no items available to pick up.", ""

            target_item = random.choice(precise_item_list)
            task = f"Search for the {target_item} and pick it up."
            verify = f"self.hold('{target_item}')"
        
        elif type==2:
            # 获取所有可访问的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "There are no items available to pick up.", ""

            target_item = random.choice(blurred_item_list)
            task = f"Search for any one {target_item} and pick it up."
            verify = f"self.hold('{target_item}')"
        
        elif type==-1:
            # miss
            out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
            target_item = random.choice(out_items)
            task = f"Search for any one {target_item} and pick it up."
            reason = f"{target_item} not exist!"
            return task, reason
        else:
            return '', ''
        
        return task, verify

    def create_place_item_task(self, type=1):
        try:
            if type==1:
                # 1. 获取所有可拿取的物品（精确名称）
                precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
                
                if not precise_item_list:
                    return "", ""

                target_item = random.choice(precise_item_list)
                receptacle = random.choice(self.get_item_precise_receptacles(target_item))

                # task = f"将{target_item}放置到{receptacle}上面/里面。"
                task = f"Place the {target_item} on/in the {receptacle}."
                verify = f"self.count_receptacle_items('{receptacle}', '{target_item}')>=1"
            
            elif type==2:
                # 获取所有可访问的物品，包括容器、物品
                blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
                blurred_item_list = list(set(blurred_item_list))

                if not blurred_item_list:
                    return "", ""

                target_item = random.choice(blurred_item_list)
                receptacle = random.choice(self.get_item_precise_receptacles(target_item))
                # task = f"将任意一个{target_item}放置到{receptacle}上面/里面。"
                task = f"Place any one {target_item} on/in the {receptacle}."

                verify = f"self.count_receptacle_items('{receptacle}', '{target_item}')>=1"
            
            elif type==3:
                # 1. 获取所有可拿取的物品（精确名称）
                precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
                
                if not precise_item_list:
                    return "", ""

                target_item = random.choice(precise_item_list)
                receptacle = random.choice(self.get_item_all_receptacles(target_item))

                # task = f"将{target_item}放置到任意一个{receptacle}上面/里面。"
                task = f"Place the {target_item} on/in any one {receptacle}."
                verify = f"self.count_receptacle_items('{receptacle}', '{target_item}')>=1"
            
            elif type==4:
                # 获取所有可访问的物品，包括容器、物品
                blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
                blurred_item_list = list(set(blurred_item_list))
                if not blurred_item_list:
                    return "", ""

                target_item = random.choice(blurred_item_list)
                receptacle = random.choice(self.get_item_all_receptacles(target_item))

                # task = f"将任意一个{target_item}放置到任意一个{receptacle}上面/里面。"
                task = f"Place any one {target_item} on/in any one {receptacle}."
                verify = f"self.count_receptacle_items('{receptacle}', '{target_item}')>=1"
            elif type==-1:
                # miss
                in_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)>0 and ITEM_ATTRIBUTES[item]['pickable']]
                out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
                if random.random()<0.5:
                    target_item = random.choice(out_items)
                    target_receptacle = random.choice(self.get_item_all_receptacles(target_item))
                    if self.get_item_count(target_receptacle)>0:
                        reason = f"{target_item} not exist!"
                    else:
                        reason = f"{target_item} not exist and {target_receptacle} not exist"
                    task = f"Place any one {target_item} on/in any one {target_receptacle}."
                else:
                    target_item = random.choice(in_items)
                    target_receptacle = random.choice(self.get_item_receptacles_notin_items(target_item))
                    task = f"Place any one {target_item} on/in any one {target_receptacle}."
                    reason = f"{target_receptacle} not exist!"
                return task, reason
            else:
                return '', ''
        except Exception as e:
            return '', ''
        return task, verify
    
    def create_toggle_on_item_task(self, type=1):
        
        if type==1:
            precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['toggleable']]
            if not precise_item_list:
                return "There are no toggleable items available.", ""
            target_item = random.choice(precise_item_list)
            task = f"Search for the {target_item} and turn on it."
            verify = f"self.toggled('{target_item}')"
        elif type==2:
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1 and self.items[item].attributes['toggleable']]
            if not blurred_item_list:
                return "There are no toggleable items available.", ""
            target_item = random.choice(blurred_item_list)
            task = f"Search for any one {target_item} and turn on it."
            verify = f"self.toggled('{target_item}')"
        else:
            return '', ''
        return task, verify
          
    def create_toggle_off_item_task(self, type=1):
        
        if type==1:
            precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['toggleable']]
            if not precise_item_list:
                return "There are no toggleable items available.", ""
            target_item = random.choice(precise_item_list)
            task = f"Search for the {target_item} and turn off it."
            verify = f"not self.toggled('{target_item}')"
        elif type==2:
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1 and self.items[item].attributes['toggleable']]
            if not blurred_item_list:
                return "There are no toggleable items available.", ""
            target_item = random.choice(blurred_item_list)
            task = f"Search for any one {target_item} and turn off it."
            verify = f"not self.toggled('{target_item}')"
        else:
            return '', ''
        return task, verify
    
    # Advanced tasks ------------------------------------------------------------------------------------- #
    # num place
    def create_multiple_item_place_task(self, item_list):
        def split_count(total, parts):
            """将一个总数 (total) 随机分割成 N 个 (parts) 大于等于 1 的正整数。使用“隔板法”（Stars and Bars）。"""
            if parts == 1:
                return [total]
            
            # 在 1 到 total - 1 之间随机选择 parts - 1 个分割点
            # 例如：total=10, parts=3。从 [1, 2, ..., 9] 中选 2 个点。
            # 如果选中 3, 7，则结果为：3, (7-3)=4, (10-7)=3 -> [3, 4, 3]
            split_points = sorted(random.sample(range(1, total), parts - 1))

            counts = []

            # 第一个部分：从 0 到第一个分割点
            counts.append(split_points[0])

            # 中间的部分：相邻分割点之间的差值
            for i in range(parts - 2):
                counts.append(split_points[i+1] - split_points[i])

            # 最后一个部分：从最后一个分割点到总数
            counts.append(total - split_points[-1])

            return counts

        counts = [self.get_item_count(item_name) for item_name in item_list]
        receptacles = [self.get_item_precise_receptacles(item_name) for item_name in item_list]
        all_task_parts = []
        all_verify_parts = []

        # 遍历每一种物品及其对应的数量和可用容器
        for item_name, item_total_count, available_receptacles in zip(item_list, counts, receptacles):
            num_available_receptacles = len(available_receptacles)
            
            if item_total_count == 0 or num_available_receptacles == 0:
                continue # 跳过无法操作的物品
                
            # 1. 决定本次任务使用的物品总数 (C)
            # 至少用 1 个，最多用到物品的全部数量
            count_to_use = random.randint(1, item_total_count)

            # 2. 决定本次任务使用的容器数量 (N)
            # N 必须 <= 可用容器数，且 N 必须 <= 物品数 (确保每个容器至少分到 1 个)
            max_n = min(count_to_use, num_available_receptacles)
            num_receptacles_to_use = random.randint(1, max_n) 

            # 3. 随机选择 N 个不同的容器
            selected_receptacles = random.sample(available_receptacles, num_receptacles_to_use)

            # 4. 将物品总数 C 分割成 N 个部分
            item_counts = split_count(count_to_use, num_receptacles_to_use)

            # 5. 生成该物品的任务和验证子字符串
            current_item_task_parts = []
            current_item_verify_parts = []
            
            for item_c, receptacle_name in zip(item_counts, selected_receptacles):
                # 任务子句：放置 X 个 item_name 到 receptacle_name
                if self.get_item_count(receptacle_name.split('_')[0].lower())>1:
                    current_item_task_parts.append(f"Place {item_c} {item_name} on/in any one {receptacle_name.split('_')[0].lower()}")
                else:
                    current_item_task_parts.append(f"Place {item_c} {item_name} on/in the {receptacle_name}")
                # 验证子句：检查 receptacle_name 中 item_name 的数量是否等于 X
                current_item_verify_parts.append(f"self.count_receptacle_items('{receptacle_name}', '{item_name}')=={item_c}")

            # 将该物品的所有放置指令连接起来 (例如：放置3个苹果到篮子，放置2个苹果到箱子)
            all_task_parts.append(", ".join(current_item_task_parts))
            # 将该物品的所有验证条件连接起来
            all_verify_parts.extend(current_item_verify_parts) # 使用 extend 添加所有验证条件
            
        # 最终任务字符串：用逗号连接所有物品的放置指令
        task = ", ".join(all_task_parts)
        # 最终验证字符串：用 and 连接所有验证条件
        verify = " and ".join(all_verify_parts)

        return task, verify
    
    # category place
    def create_category_item_task(self, type=1):
        
        # 1. 定义物品类别字典
        categories = {
            1: {
                'name': "all fruits",
                'items': ['apple', 'tomato'],  # 注意：在常识中tomato是水果，但游戏中可能按蔬菜分类
                'receptacle_name': "receptacle"
            },
            2: {
                'name': "all vegetables",
                'items': ['lettuce', 'potato'],
                'receptacle_name': "receptacle"
            },
            3: {
                'name': "all knives, forks, and spoons",
                'items': ['butterknife', 'ladle', 'knife', 'spoon', 'fork'],
                'receptacle_name': "drawer or utensil rack"
            },
            4: {
                'name': "all seasoning bottles",
                'items': ['peppershaker', 'saltshaker'],
                'receptacle_name': "shelf or cabinet"
            },
            5: {
                'name': "all the pots",
                'items': ['pot', 'pan'],
                'receptacle_name': "cabinet or stove"
            },
            6: {
                'name': "all utensils used to hold food/drinks",
                'items': ['mug', 'cup', 'plate', 'bowl'],
                'receptacle_name': "utensil cabinet"
            }
        }
        
        # 检查 type 是否有效
        if type not in categories:
            return f"Error: Unsupported category type {type}", ""

        category_info = categories[type]
        category_items = category_info['items']
        category_name = category_info['name']
        
        item_counts = []
        
        for item_name in category_items:
            item_counts.append(self.get_item_count(item_name))

        if sum(item_counts) == 0:
            return f"Task failed: No {category_name} items found in the scene.", ""

        # 3. 找到所有物品的公共容器 (Common receptacles)    
        # 从第一个物品开始初始化公共容器列表
        common_receptacles = set(self.get_item_all_receptacles(category_items[0]))
        
        # 与剩余物品的容器取交集
        for item_name in category_items[1:]:
            current_item_receptacles = set(self.get_item_all_receptacles(item_name))
            common_receptacles &= current_item_receptacles
            
            # 如果交集为空，则提前退出，无法生成公共容器任务
            if not common_receptacles:
                # 任务失败：无法找到一个容器能装下该类别所有物品
                return f"Task failed: No receptacle found that can hold all {category_name} items.", ""

        # 4. 随机选择一个公共容器
        receptacle_list = list(common_receptacles)
        receptacle = random.choice(receptacle_list)
        # 5. 生成任务字符串
        if self.get_item_count(receptacle.split('_')[0].lower()) > 1:
            # task = f"将{category_name}放置{receptacle}上面/里面。"
            task = f"Place {category_name} on/in any one {receptacle.split('_')[0].lower()}."
            verify = f"self.verify_category_place_task('{receptacle.split('_')[0].lower()}', {category_items}, {item_counts})"
        else:
            task = f"Place {category_name} on/in the {receptacle}."
            verify = f"self.verify_category_place_task('{receptacle}', {category_items}, {item_counts})"

        # 6. 生成验证字符串 (verify)
        # 验证逻辑是：该类别所有物品（精确名称）都应该位于选定的容器中
        # verify_parts = []
        # # 为该类别的每一个精确物品生成验证子句
        # for item_name, count in zip(category_items, item_counts):
        #     verify_parts.append(f"self.count_receptacle_items('{receptacle}', '{item_name}')=={count}")
        # verify = " and ".join(verify_parts)
        
        return task, verify

    # order visit
    def create_order_visit_item_task_by_index(self, type=1):
        """
        生成一个要求按照数字索引顺序访问多个物品的任务。
        :return: task (str), verify (str)
        """
        # 每个 item 相互独立
        def check_valid(items):
            for item in items:
                for x in items:
                    if self.count_receptacle_items(item, x) > 0:
                        return False
            return True

        if type==1:
            # 1. 获取所有可访问的物品（精确名称）
            precise_item_list = [item for item in self.items if self.items[item].level > 1]
            
            if not precise_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(precise_item_list), 5)
            
            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(precise_item_list, use_count)
            if not check_valid(base_items):
                return '', ''
        
        elif type==2:
            # 获取所有可访问的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(blurred_item_list), 5)
            
            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(blurred_item_list, use_count)
            if not check_valid(base_items):
                return '', ''
        
        elif type == -1:
            # 获取所有可访问的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level > 1]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(blurred_item_list), 5)
            
            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(blurred_item_list, use_count)

            # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
            index_order = list(range(1, use_count + 1))
            random.shuffle(index_order) 
            
            # c. 目标访问顺序列表 (target_order_list) - 用于验证的实际物品名称列表
            target_order_list = [base_items[idx - 1] for idx in index_order]
            out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
            out_receptacles = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['placeable']]
            out_item = random.choice(out_items+out_receptacles)
            replace_index = random.randint(0, len(base_items))
            base_items[replace_index] = out_item
            # 4. 生成任务字符串
            task = f"There are some items: {base_items}, and the access priority of these items is {index_order}. Please access these items in ascending order of priority."
            reason = f"{out_item} not exist!"
            return task, reason
        
        else:
            return '', ''
        
        # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
        index_order = list(range(1, use_count + 1))
        random.shuffle(index_order) 
        
        # c. 目标访问顺序列表 (target_order_list) - 用于验证的实际物品名称列表
        target_order_list = [base_items[idx - 1] for idx in index_order]

        # 4. 生成任务字符串
        task = f"There are some items: {base_items}, and the access priority of these items is {index_order}. Please access these items in ascending order of priority."
        
        # 5. 生成验证字符串 (verify)
        verify = f"self.verify_order_visited_task({base_items},{index_order})"
        
        return task, verify

    # order pickup
    def create_order_pickup_item_task_by_index(self, type=1):
        """
        生成一个要求按照数字索引顺序访问多个物品的任务。
        :return: task (str), verify (str)
        """
        if type==1:
            # 1. 获取所有可访问的物品（精确名称）
            precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
            
            if not precise_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(precise_item_list), 5)
            
            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(precise_item_list, use_count)
            
        elif type==2:
            # 获取所有可拿取的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1 and self.items[item].attributes['pickable']]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(blurred_item_list), 5)

            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(blurred_item_list, use_count)
        elif type==-1:
            # 获取所有可拿取的物品，包括容器、物品
            blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1 and self.items[item].attributes['pickable']]
            blurred_item_list = list(set(blurred_item_list))

            if not blurred_item_list:
                return "No accessible items.", ""

            # 2. 确定要使用的物品数量 (use_count)
            max_count = min(len(blurred_item_list), 5)

            if max_count < 2:
                return "Accessible items are less than 2, cannot form a sequential access task.", ""
            use_count = random.randint(2, max_count)
            
            # 3. 确定两个关键列表
            base_items = random.sample(blurred_item_list, use_count)
             # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
            index_order = list(range(1, use_count + 1))
            random.shuffle(index_order) 
            # c. 目标访问顺序列表 (target_order_list) - 用于验证的实际物品名称列表
            target_order_list = [base_items[idx - 1] for idx in index_order]
            out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
            out_item = random.choice(out_items)
            replace_index = random.randint(0, len(base_items))
            base_items[replace_index] = out_item
            # 4. 生成任务字符串
            task = f"There are some items: {base_items}, and the priority for taking these items is {index_order}. Please take them in ascending order of priority."
            reason = f"{out_item} not exist!"
            return task, reason
        else:
            return '', ''
        
        # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
        index_order = list(range(1, use_count + 1))
        random.shuffle(index_order) 
        
        # c. 目标访问顺序列表 (target_order_list) - 用于验证的实际物品名称列表
        target_order_list = [base_items[idx - 1] for idx in index_order]

        # 4. 生成任务字符串
        task = f"There are some items: {base_items}, and the priority for taking these items is {index_order}. Please take them in ascending order of priority."

        # 5. 生成验证字符串 (verify)
        verify = f"self.verify_order_pickup_task({base_items}, {index_order})"
        
        return task, verify

    # order place
    def create_order_place_item_task_by_index(self, type=1):
        """
        生成一个要求按照数字索引顺序访问多个物品的任务。
        :return: task (str), verify (str)
        """
        try:
            if type==1:
                # 1. 获取所有可访问的物品（精确名称）
                precise_item_list = [item for item in self.items if self.items[item].level > 1 and self.items[item].attributes['pickable']]
                if not precise_item_list:
                    return "No accessible items.", ""

                # 2. 确定要使用的物品数量 (use_count)
                max_count = min(len(precise_item_list), 5)
                
                if max_count < 2:
                    return "Accessible items are less than 2, cannot form a sequential access task.", ""
                use_count = random.randint(2, max_count)
                
                # 3. 确定两个关键列表
                base_items = random.sample(precise_item_list, use_count)
                base_receptacles = [random.choice(self.get_item_precise_receptacles(i)) for i in base_items]

                # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
                index_order = list(range(1, use_count + 1))
                random.shuffle(index_order) 
                
                # c. 目标访问顺序列表 (target_order_list) - 用于验证的实际物品名称列表
                # target_order_list = [base_items[idx - 1] for idx in index_order]
            
            elif type==2:

                blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1 and self.items[item].attributes['pickable']]
                blurred_item_list = list(set(blurred_item_list))

                if not blurred_item_list:
                    return "No accessible items.", ""

                # 2. 确定要使用的物品数量 (use_count)
                max_count = min(len(blurred_item_list), 5)
                
                if max_count < 2:
                    return "Accessible items are less than 2, cannot form a sequential access task.", ""
                
                use_count = random.randint(2, max_count)
                
                # 3. 确定两个关键列表
                base_items = random.sample(blurred_item_list, use_count)
                base_receptacles = [random.choice(self.get_item_receptacles(i)) for i in base_items]

                # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
                index_order = list(range(1, use_count + 1))
                random.shuffle(index_order)
            
            elif type==-1:
                blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1 and self.items[item].attributes['pickable']]
                blurred_item_list = list(set(blurred_item_list))

                if not blurred_item_list:
                    return "No accessible items.", ""

                # 2. 确定要使用的物品数量 (use_count)
                max_count = min(len(blurred_item_list), 5)
                
                if max_count < 2:
                    return "Accessible items are less than 2, cannot form a sequential access task.", ""
                
                use_count = random.randint(2, max_count)
                
                # 3. 确定两个关键列表
                base_items = random.sample(blurred_item_list, use_count)
                base_receptacles = [random.choice(self.get_item_receptacles(i)) for i in base_items]

                # b. 数字索引列表 (index_order) - 验证目标，即 [3, 5, 1, 4, 2] 这种顺序
                index_order = list(range(1, use_count + 1))
                random.shuffle(index_order)
                replace_index = random.randint(0, len(base_items))

                out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
                out_item = random.choice(out_items)
                if random.random()<0.7:
                    base_items[replace_index] = out_item
                    if random.random()<0.5:
                        out_receptacle = random.choice(self.get_item_receptacles_notin_items(base_items[replace_index])).split('_')[0].lower()
                        base_receptacles[replace_index] = out_receptacle
                        reason = f"{out_item} not exist and {out_receptacle} not exist!"
                    else:
                        reason = f"{out_item} not exist!"
                else:
                    out_receptacle = random.choice(self.get_item_receptacles_notin_items(base_items[replace_index])).split('_')[0].lower()
                    base_receptacles[replace_index] = out_receptacle
                    reason = f"{out_receptacle} not exist!"
                
                task = f"Here are some items: {base_items}. Please place them in/on {base_receptacles} respectively. The placement priority is {index_order}. Please place them in ascending order of priority."
                return task, reason
            
            else:
                return '', ''
            # 4. 生成任务字符串
            task = f"这有一些物品:{base_items}，请将它们分别放置{base_receptacles}, 放置的优先级为{index_order}. 请按照优先级从低到高依次放置。"
            task = f"Here are some items: {base_items}. Please place them in/on {base_receptacles} respectively. The placement priority is {index_order}. Please place them in ascending order of priority."
            
            # 5. 生成验证字符串 (verify)
            verify = f"self.verify_order_place_task({base_items}, {base_receptacles}, {index_order})"
            
            return task, verify
        
        except Exception as e:
            return '', ''

    # conditional visited
    def create_conditional_navigate_task(self, type=1):
        uncertain_items = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['pickable']]
        uncertain_receptacles = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['placeable']]
        in_items = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('pickable', False)
        ]
        in_items = list(set(in_items))
        in_receptacles = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('placeable', False)
        ]
        in_receptacles = list(set(in_receptacles))
        out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
        out_receptacles = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['placeable']]
        try:
            # exist a
            if type==1:
                # 存在primary_receptacle，fallback_receptacle不一定存在
                # 不存在primary_receptacle，fallback_receptacle存在
                if len(in_receptacles)<1:
                    return '', ''
                if random.random() < 0.3:
                    primary_receptacle_or_item = random.choice(in_receptacles+in_items)
                    fallback_receptacle_or_item = random.choice(uncertain_receptacles+uncertain_items)
                else:
                    primary_receptacle_or_item = random.choice(out_receptacles+out_items)
                    fallback_receptacle_or_item = random.choice(in_receptacles+in_items)
                
                # task = f"搜索{primary_receptacle_or_item}, 并导航到任意一个面前. \
                #         如果{primary_receptacle_or_item}不存在，则导航到任意一个{fallback_receptacle_or_item}."
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {primary_receptacle_or_item} does not exist, navigate to any one of {fallback_receptacle_or_item}."
                verify = f"(self.exist('{primary_receptacle_or_item}') and self.located('{primary_receptacle_or_item}'))\
                        or (not self.exist('{primary_receptacle_or_item}') and self.located('{fallback_receptacle_or_item}'))"
            
            # saw a
            elif type==2:
                # 存在primary_receptacle，receptacle不存在，fallback_receptacle不一定存在
                # 存在primary_receptacle，receptacle存在，fallback_receptacle存在
                # 不存在primary_receptacle，receptacle存在，fallback_receptacle存在
                if len(in_receptacles)<3:
                    return '', ''
                if random.random() < 0.5:
                    if random.random() < 0.5:
                        primary_receptacle_or_item = random.choice(in_receptacles+in_items)
                        receptacle_or_item = random.choice(out_receptacles+in_items)
                        fallback_receptacle_or_item = random.choice(uncertain_receptacles+uncertain_items)
                    else:
                        primary_receptacle_or_item, receptacle_or_item, fallback_receptacle_or_item = random.sample(in_receptacles+in_items, 3)
                else:
                    primary_receptacle_or_item = random.choice(out_receptacles+out_items)
                    receptacle_or_item, fallback_receptacle_or_item = random.sample(in_receptacles+in_items, 2)
                
                # task = f"搜索{primary_receptacle_or_item}, 并导航到任意一个面前. \
                #         如果在搜索过程中发现了{receptacle_or_item}，则导航到任意一个{fallback_receptacle_or_item}." # 动态
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {receptacle_or_item} is found during the search, navigate to any one {fallback_receptacle_or_item}."
                verify = f"(self.saw('{receptacle_or_item}') and self.located('{fallback_receptacle_or_item}')) or \
                        (not self.saw('{receptacle_or_item}') and self.located('{primary_receptacle_or_item}'))"
            
            # count a
            elif type==3:
                # primary_receptacle存在，item不存在，fallback_receptacle不一定存在
                # primary_receptacle存在，item存在且小于等于n，fallback_receptacle不一定存在
                # primary_receptacle存在，item存在且大于n，fallback_receptacle一定存在
                # primary_receptacle不存在，item存在且item数量大于n，fallback_receptacle一定存在
                if random.random() < 0.5:
                    primary_receptacle_or_item, temp = random.sample(in_receptacles+in_items, 2)
                    if random.random() < 0.5:
                        item = random.choice(out_items)
                        fallback_receptacle_or_item = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([primary_receptacle_or_item])))
                        n = random.randint(1, 3)
                    else:
                        counts = [self.get_item_count(x) for x in in_items]
                        item = random.choice(in_items)
                        n = random.choice(counts)
                        if self.get_item_count(item) <= n:
                            fallback_receptacle_or_item = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([primary_receptacle_or_item])))
                        else:
                            fallback_receptacle_or_item = temp
                            
                else:
                    primary_receptacle_or_item = random.choice(out_receptacles+out_items)
                    counts = [self.get_item_count(x) for x in in_items]
                    index = random.randint(0, len(in_items)-1)
                    n = random.randint(1, counts[index])
                    item = in_items[index]
                    fallback_receptacle_or_item = random.choice(in_receptacles+in_items)
                
                # task = f"搜索{primary_receptacle}, 并导航到任意一个面前. \
                #         如果{item}存在 并且 数量大于{n}，则导航到任意一个{fallback_receptacle}." # 必须先检查
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {item} exists and the quantity is greater than {n}, navigate to any {fallback_receptacle_or_item}."
                verify = f"(self.count('{item}')>{n} and self.located('{fallback_receptacle_or_item}'))\
                        or (self.count('{item}')<={n} and self.located('{primary_receptacle_or_item}'))"
            
            # visited a
            elif type==4:
                primary_receptacle_or_item, fallback_receptacle_or_item = random.sample(in_receptacles+in_items, 2)
                receptacle = random.choice([x for x in uncertain_receptacles if x not in [primary_receptacle_or_item, fallback_receptacle_or_item]])
                task = f"搜索{primary_receptacle_or_item}, 并导航到任意一个面前. \
                        如果在搜索过程中访问了{receptacle}，则导航到任意一个{fallback_receptacle_or_item}." # 动态
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {receptacle} is accessed during the search, navigate to any {fallback_receptacle_or_item}."
                verify = f"(not self.visited('{receptacle}') and self.located('{primary_receptacle_or_item}'))\
                        or (self.visited('{receptacle}') and self.located('{fallback_receptacle_or_item}'))"
            
            # a in b
            elif type==5:
                # primary_receptacle存在，receptacle不一定存在，item不存在，fallback_receptacle不一定存在
                # primary_receptacle存在，receptacle存在，item存在且数量小于n，fallback_receptacle不一定存在
                # primary_receptacle存在，receptacle不存在，item存在且数量小于n，fallback_receptacle不一定存在
                # primary_receptacle存在，receptacle存在，item存在且数量等于n，fallback_receptacle存在
                # primary_receptacle不存在，receptacle存在，item存在且数量等于n，fallback_receptacle存在
                receptacle = random.choice(uncertain_receptacles)
                item = random.choice([x for x in receptacle2ITEMS[receptacle]])
                if self.get_item_count(receptacle) > 0:
                    if self.count_receptacle_items(receptacle, item) > 0:
                        fallback_receptacle_or_item = random.choice(in_receptacles+in_items)
                        primary_receptacle_or_item = random.choice([x for x in uncertain_receptacles+in_items if x!=fallback_receptacle_or_item])
                    else:
                        primary_receptacle_or_item = random.choice(in_receptacles+in_items)
                        fallback_receptacle_or_item = random.choice([x for x in uncertain_receptacles+in_items if x!=primary_receptacle_or_item])
                else:
                    primary_receptacle_or_item = random.choice(in_receptacles+in_items)
                    fallback_receptacle_or_item = random.choice([x for x in uncertain_receptacles+in_items if x!=primary_receptacle_or_item])

                # task = f"搜索{primary_receptacle}, 并导航到任意一个面前. \
                #         如果存在{receptacle} 并且 上面/里面有{item}，则导航到任意一个{fallback_receptacle}." # 必须先检查
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {receptacle} exists and there is {item} on it/in it, navigate to any {fallback_receptacle_or_item}."

                verify = f"(self.exist('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')>0 and self.located('{fallback_receptacle_or_item}')) or \
                        ((not self.exist('{receptacle}') or (self.exist('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')==0)) and self.located('{fallback_receptacle_or_item}'))"
                
            # exist | saw
            elif type==6:
                if random.random() < 0.5:
                    primary_receptacle_or_item = random.choice(in_receptacles+in_items)
                    fallback_receptacle_or_item = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([primary_receptacle_or_item])))
                    if random.random() < 0.5:
                        receptacle_or_item = random.choice(list(set(out_receptacles+out_items) - set([fallback_receptacle_or_item])))
                        fallback_receptacle_or_item_2 = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([primary_receptacle_or_item, receptacle_or_item, fallback_receptacle_or_item])))
                    else:
                        receptacle_or_item = random.choice(list(set(in_receptacles+in_items) - set([primary_receptacle_or_item, fallback_receptacle_or_item])))
                        fallback_receptacle_or_item_2 = random.choice(list(set(in_receptacles+in_items) - set([primary_receptacle_or_item, fallback_receptacle_or_item, receptacle_or_item])))
                else:
                    primary_receptacle_or_item, temp = random.sample(out_receptacles+out_items, 2)
                    if random.random() < 0.5:
                        fallback_receptacle_or_item = random.choice(in_receptacles+in_items)
                        receptacle_or_item = temp
                        fallback_receptacle_or_item_2 = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([primary_receptacle_or_item, fallback_receptacle_or_item, receptacle_or_item])))
                    else:
                        fallback_receptacle_or_item = temp
                        receptacle_or_item, fallback_receptacle_or_item_2 = random.sample(in_receptacles+in_items, 2)

                # task = f"搜索{primary_receptacle_or_item}, 并导航到任意一个面前. \
                #         如果{primary_receptacle_or_item}不存在，则导航到任意一个{fallback_receptacle_or_item}面前. \
                #         如果在搜索过程中发现了{receptacle_or_item}，则导航到任意一个{fallback_receptacle_or_item_2}面前." # 动态
                task = f"Search for {primary_receptacle_or_item} and navigate to the front of any one of them. If {primary_receptacle_or_item} does not exist, navigate to the front of any one of {fallback_receptacle_or_item}. If {receptacle_or_item} is found during the search, navigate to the front of any one of {fallback_receptacle_or_item_2}."
                verify = f"(self.saw('{receptacle_or_item}') and self.located('{fallback_receptacle_or_item_2}')) \
                        or (not self.saw('{receptacle_or_item}') and self.exist('{primary_receptacle_or_item}') and self.located('{primary_receptacle_or_item}')) \
                        or (not self.saw('{receptacle_or_item}') and not self.exist('{primary_receptacle_or_item}') and self.located('{fallback_receptacle_or_item}'))"
            
            # exist | count
            elif type==7:
                primary_receptacle_or_item = random.choice(uncertain_receptacles+uncertain_items)
                counts = [self.get_item_count(x) for x in in_items + out_items]
                n = random.randint(1, max(counts))
                item = random.choice(in_items + out_items)
                if self.get_item_count(primary_receptacle_or_item)==0:
                    if self.get_item_count(item)<=n:
                        fallback_receptacle_or_item_2 = random.choice([x for x in in_receptacles+in_items if x!=item])
                        fallback_receptacle_or_item = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([fallback_receptacle_or_item_2, item, primary_receptacle_or_item])))
                    elif self.get_item_count(item) > n:
                        fallback_receptacle_or_item = random.choice([x for x in in_receptacles+in_items if x!=item])
                        fallback_receptacle_or_item_2 = random.choice(list(set(uncertain_receptacles+uncertain_items) - set([fallback_receptacle_or_item, item])))
                else:
                    fallback_receptacle_or_item, fallback_receptacle_or_item_2 = random.sample([x for x in uncertain_receptacles+uncertain_items if x not in [primary_receptacle_or_item, item]], 2)
                # task = f"搜索{primary_receptacle}, 并导航到任意一个面前. \
                #         如果{primary_receptacle}不存在 \
                #         并且 {item}存在 并且 数量大于n， \
                #         则导航到任意一个{fallback_receptacle}, 否则导航到任意一个{fallback_receptacle2}."
                task = f"Search for {primary_receptacle_or_item} and navigate to any one in front of you. If {primary_receptacle_or_item} does not exist and {item} exists and the quantity is greater than {n}, then navigate to any {fallback_receptacle_or_item}; otherwise, navigate to any {fallback_receptacle_or_item_2}."
                verify = f"(self.exist('{primary_receptacle_or_item}') and self.located('{primary_receptacle_or_item}')) or \
                        (not self.exist('{primary_receptacle_or_item}') and self.count('{item}')<={n} and self.located('{fallback_receptacle_or_item_2}')) or \
                        (not self.exist('{primary_receptacle_or_item}') and self.count('{item}')>{n} and self.located('{fallback_receptacle_or_item}'))"

            # exist | count | a in b
            elif type==8:
                if len(in_receptacles)<3:
                    return '', ''
                # primary_receptacle存在，receptacle不一定存在 item 不一定存在 fallback_receptacle不一定存在 fallback_receptacle2不一定存在 fallback_receptacle3不一定存在
                # primary_receptacle不存在，receptacle存在 item存在且大于等于n fallback_receptacle存在 fallback_receptacle2不一定存在 fallback_receptacle3不一定存在 
                # primary_receptacle不存在，receptacle存在 item的数量小于n fallback_receptacle不一定存在 fallback_receptacle2存在 fallback_receptacle3不一定存在
                # primary_receptacle不存在，receptacle不存在 item不一定存在 fallback_receptacle不一定存在 fallback_receptacle2不一定存在 fallback_receptacle3存在 
                primary_receptacle_or_item = random.choice(uncertain_receptacles+uncertain_items)
                if self.get_item_count(primary_receptacle_or_item)==0:
                    if random.random() < 0.5:
                        receptacle = random.choice([x for x in uncertain_receptacles if x!=primary_receptacle_or_item])
                        item = random.choice([x for x in receptacle2ITEMS[receptacle]])
                        if self.get_item_count(receptacle)==0:
                            fallback_receptacle_or_item_3 = random.choice(in_receptacles+in_items)
                            fallback_receptacle_or_item, fallback_receptacle_or_item_2 = random.sample([x for x in uncertain_receptacles+uncertain_items if x not in [primary_receptacle_or_item, item, fallback_receptacle_or_item_3]], 2)
                        elif self.count_receptacle_items(receptacle, item) <= 0: # 不存在
                            fallback_receptacle_or_item_2 = random.choice([x for x in in_receptacles+in_items if x not in [receptacle, item]])
                            fallback_receptacle_or_item, fallback_receptacle_or_item_3 = random.sample([x for x in uncertain_receptacles if x not in [primary_receptacle_or_item, receptacle, item, fallback_receptacle_or_item_2]], 2)
                        elif self.count_receptacle_items(receptacle, item) > 0: # 存在
                            fallback_receptacle_or_item = random.choice(in_receptacles+in_items)
                            fallback_receptacle_or_item_2, fallback_receptacle_or_item_3 = random.sample([x for x in uncertain_receptacles+uncertain_items if x not in [primary_receptacle_or_item, receptacle, item, fallback_receptacle_or_item]], 2)
                    else:
                        receptacle = random.choice([x for x in self.items if len(self.items[x].contents) >= 1 and self.items[x].attributes.get('placeable', False)])
                        item_ = random.choice(list(self.items[receptacle].contents.keys()))
                        item = item_.split('_')[0]
                        fallback_receptacle_or_item = random.choice([x for x in in_receptacles+in_items if x!=item])
                        fallback_receptacle_or_item_2, fallback_receptacle_or_item_3 = random.sample([x for x in uncertain_receptacles+uncertain_items if x not in [primary_receptacle_or_item, receptacle, item, fallback_receptacle_or_item]], 2)
                else:
                    receptacle, fallback_receptacle_or_item, fallback_receptacle_or_item_2, fallback_receptacle_or_item_3 = random.sample(uncertain_receptacles+uncertain_items, 4)
                    item = random.choice(in_items + out_items)
                
                # task = f"搜索{primary_receptacle_or_item}, 并导航到任意一个面前. \
                #         如果{primary_receptacle}不存在 并且 {receptacle}存在 \
                #             如果上面/里面有{item}，则导航到任意一个{fallback_receptacle_or_item}面前, \
                #             如果上面/里面没有{item}，则导航到任意一个{fallback_receptacle_or_item_2}面前. \
                #         如果{primary_receptacle_or_item}不存在 并且 {receptacle}不存在，则导航到任意一个{fallback_receptacle_or_item_3}面前."
                task = f"Search for {primary_receptacle_or_item} and navigate to the front of any one of them. If {primary_receptacle_or_item} does not exist and {receptacle} exists If there is {item} on top of or inside it, navigate to the front of any {fallback_receptacle_or_item}, If there is no {item} on top of or inside it, navigate to the front of any {fallback_receptacle_or_item_2}. If {primary_receptacle_or_item} does not exist and {receptacle} does not exist, navigate to the front of any {fallback_receptacle_or_item_3}."
                verify = f"(not self.exist('{primary_receptacle_or_item}') and not self.exist('{receptacle}') and self.located('{fallback_receptacle_or_item_3}')) \
                        or (not self.exist('{primary_receptacle_or_item}') and self.exist('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')>=1 and self.located('{fallback_receptacle_or_item}')) \
                        or (not self.exist('{primary_receptacle_or_item}') and self.exist('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')<1 and self.located('{fallback_receptacle_or_item_2}')) \
                        or (self.exist('{primary_receptacle_or_item}') and self.located('{primary_receptacle_or_item}'))"
            else:
                return '', ''
            return task, verify
        except Exception as e:
            return '', ''
        
        # logical expression
        # exist(a); saw(a); visited(a); count(a) > n; a in b; 
        # 1. navigate： navigate to a... if logic else navigate to b...
        # 2. pickup：pickup a... if logic else pickup b...
        # 3. place：place a in b if logic else place a in c
    
    # conditional pickup
    def create_conditional_pickup_task(self, type=1):
        # # pickup
        # task = f"搜索{primary_item}, 并拿起它. 如果{primary_item}不存在, 则拿起{fallback_item}."
        # task = f"搜索{primary_item}, 并拿起它. 如果在搜索的过程中发现了{}, 则拿起{fallback_item}."
        # task = f"搜索{primary_item}, 并拿起它. 如果{}的数量nxxx, 则拿起{fallback_item}."
        # task = f"搜索{primary_item}, 并拿起它. 如果{}上面/里面有{}, 则拿起{fallback_item}."
        uncertain_items = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['pickable']]
        uncertain_receptacles = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['placeable']]
        in_items = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('pickable', False)
        ]
        in_items = list(set(in_items))
        in_receptacles = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('placeable', False)
        ]
        in_receptacles = list(set(in_receptacles))
        out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
        out_receptacles = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['placeable']]

        try:
            # exist a
            if type == 1:
                primary_item, temp = random.sample(uncertain_items, 2)
                if self.get_item_count(primary_item)>0:
                    fallback_item = temp
                else:
                    fallback_item = random.choice(in_items)
                # task = f"搜索{primary_item}, 并拿起它. 如果{primary_item}不存在, 则搜索并拿起{fallback_item}."
                task = f"Search for {primary_item} and pick it up. If {primary_item} does not exist, search for and pick up {fallback_item}."
                verify = f"(self.exist('{primary_item}') and self.hold('{primary_item}')) \
                        or (not self.exist('{primary_item}') and self.hold('{fallback_item}'))"
            
            # saw a
            elif type == 2:
                primary_item, temp = random.sample(in_items, 2)
                item = random.choice([x for x in uncertain_items if x!=primary_item])
                if self.get_item_count(item)>0:
                    fallback_item = temp
                else:
                    fallback_item = random.choice([x for x in uncertain_items if x!=primary_item])
                # task = f"搜索{primary_item}, 并拿起它. 如果在搜索的过程中发现了{item}, 则搜索并拿起{fallback_item}."
                task = f"Search for {primary_item} and pick it up. If {item} is found during the search, search for and pick up {fallback_item}."
                verify = f"(not self.saw('{item}') and self.hold('{primary_item}')) \
                        or (self.saw('{item}') and self.hold('{fallback_item}'))"
            
            # count a
            elif type == 3:
                item = random.choice(uncertain_items)
                if self.get_item_count(item) > 0:
                    n = random.randint(0, 2*self.get_item_count(item))
                else:
                    n = random.randint(0, 4)
                primary_item, fallback_item = random.sample(in_items, 2)
                if self.get_item_count(item) <= n:
                    fallback_item = random.choice([x for x in uncertain_items if x not in [primary_item, item]])

                # task = f"搜索{primary_item}, 并拿起它. 如果{item}的数量大于n, 则拿起{fallback_item}."
                task = f"Search for {primary_item} and pick it up. If the quantity of {item} is greater than {n}, search for and pick up {fallback_item}."
                verify = f"(self.count('{item}')<={n} and self.hold('{primary_item}')) \
                        or (self.count('{item}')>{n} and self.hold('{fallback_item}'))"
            
            # visited a
            elif type == 4:
                primary_item, fallback_item = random.sample(in_items, 2)
                receptacle = random.choice(in_receptacles)
                # task = f"搜索{primary_item}, 并拿起它. 如果在这期间访问了{receptacle}, 则拿起{fallback_item}."
                task = f"Search for {primary_item} and pick it up. If {receptacle} is accessed during this period, pick up {fallback_item}."
                verify = f"(not self.visited('{receptacle}') and self.hold('{primary_item}')) \
                        or (self.visited('{receptacle}') and self.hold('{fallback_item}'))"
            
            # a in b
            elif type == 5:
                receptacle = random.choice(uncertain_receptacles)
                items = self.get_item_contents(receptacle)
                item = random.choice(uncertain_items + items)
                # receptacle = random.choice(self.get_item_receptacles(item))
                if self.count_receptacle_items(receptacle, item)>0:
                    fallback_item = random.choice([x for x in in_items if x!=item])
                    primary_item = random.choice([x for x in uncertain_items if x not in [fallback_item, item]])
                else:
                    primary_item = random.choice(in_items)
                    fallback_item = random.choice([x for x in uncertain_items if x not in[primary_item, item]])

                # task = f"搜索{primary_item}, 并拿起它. 如果{receptacle}上面/里面有{item}, 则拿起{fallback_item}."
                task = f"Search for {primary_item} and pick it up. If there is {item} on/in {receptacle}, search for and pick up {fallback_item}."
                verify = f"(self.count_receptacle_items('{receptacle}', '{item}')>0 and self.hold('{fallback_item}')) \
                        or (self.count_receptacle_items('{receptacle}', '{item}')<0 and self.hold('{primary_item}'))"
            
            # exist | a in b
            elif type == 6:
                primary_item = random.choice(uncertain_items)
                if self.get_item_count(primary_item) == 0:
                    fallback_item = random.choice([x for x in in_items if x!=primary_item])
                else:
                    fallback_item = random.choice([x for x in uncertain_items if x!=primary_item])
                
                receptacle = random.choice(uncertain_receptacles)
                items = self.get_item_contents(receptacle)
                item = random.choice([x for x in uncertain_items + items if x not in [primary_item, fallback_item]])
                if self.count_receptacle_items(receptacle, item) > 0:
                    fallback_item2 = random.choice([x for x in in_items if x not in [primary_item, fallback_item]])
                else:
                    fallback_item2 = random.choice([x for x in uncertain_items if x not in [primary_item, fallback_item]])
                
                # task = f"搜索{primary_item}, 并拿起它。如果{primary_item}不存在，则搜索并拿起{fallback_item}. \
                        # 如果在搜索的过程中发现了{receptacle}, 并且它上面/里面存在{item}, 则搜索并拿起{fallback_item2}。"
                task = f"Search for {primary_item} and pick it up. If {primary_item} does not exist, search for and pick up {fallback_item}. If {receptacle} is found during the search and there is {item} on/in it, search for and pick up {fallback_item2}."
                verify = f"(not self.saw('{receptacle}') and self.exist('{primary_item}') and self.hold('{primary_item}')) \
                        or (not self.saw('{receptacle}') and not self.exist('{primary_item}') and self.hold('{fallback_item}')) \
                        or (self.saw('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')>0 and self.hold('{fallback_item2}'))"
            
            # exist | a in b
            elif type == 7:
                primary_item = random.choice(uncertain_items)
                receptacle = random.choice(uncertain_receptacles)
                if self.get_item_count(primary_item) == 0:
                    if self.get_item_count(receptacle) == 0:
                        item, item2, fallback_item = random.sample([x for x in uncertain_items if x!=primary_item], 3)
                        fallback_item2 = random.choice([x for x in in_items if x not in [primary_item, item, item2, fallback_item]])
                    else:
                        items = self.get_item_contents(receptacle)
                        item, item2 = random.sample(items+uncertain_items, 2)
                        if self.count_receptacle_items(receptacle, item)==0 and self.count_receptacle_items(receptacle, item2)==0:
                            fallback_item = random.choice(in_items)
                            fallback_item2 = random.choice([x for x in uncertain_items if x!=primary_item])
                        else:
                            fallback_item, fallback_item2 = random.sample([x for x in uncertain_items if x!=primary_item], 2)
                else:
                    item, item2, fallback_item, fallback_item2 = random.sample([x for x in uncertain_items if x!=primary_item], 4)
                
                # task = f"搜索{primary_item}, 并拿起它。
                # 如果{primary_item}不存在，并且{receptacle}存在，
                    # 如果{receptacle}上面/里面有{item}或者{item2}, 则拿起任意一个{item}或者{item2}, 
                    # 如果{receptacle}上面/里面没有{item}、{item2},则搜索并拿起{fallback_item}. 
                # 如果{primary_item}不存在，并且{receptacle}不存在, 则搜索并拿起{fallback_item2}。"
                task = f"Search for {primary_item} and pick it up. If {primary_item} does not exist and {receptacle} exists, if there is {item} or {item2} on/in {receptacle}, pick up any {item} or {item2}; if there is no {item} or {item2} on/in {receptacle}, search for and pick up {fallback_item}. If {primary_item} does not exist and {receptacle} does not exist, search for and pick up {fallback_item2}."
                verify = f"(self.exist('{primary_item}') and self.hold('{primary_item}')) \
                        or (not self.exist('{primary_item}') and self.exist('{receptacle}') and (self.count_receptacle_items('{receptacle}', '{item}')>0 or self.count_receptacle_items('{receptacle}', '{item2}')>0) and (self.hold('{item}') or self.hold('{item2}')) ) \
                        or (not self.exist('{primary_item}') and self.exist('{receptacle}') and self.count_receptacle_items('{receptacle}', '{item}')==0 and self.count_receptacle_items('{receptacle}', '{item2}')==0 and self.hold('{fallback_item}') ) \
                        or (not self.exist('{primary_item}') and not self.exist('{receptacle}') and self.hold('{fallback_item2}'))"
            
            else:
                return '', ''
            return task, verify
        except Exception as e:
            return '', ''
    
    # conditioanl place
    def create_conditional_place_task(self, type=1):
        # place
        # task = f"将{primary_item}放到{primary_receptacle}. 如果{primary_receptacle}不存在, 则将物品放到{fallback_receptacle}; 如果{primary_item}不存在，则将{fallback_item}放到{primary_receptacle}. 如果两者都不存在，则将{fallback_item}放到{fallback_receptacle}."
        # task = f"将{fallback_item}放到{fallback_receptacle}. 如果在搜索的过程中发现了{}, 则将物品放到{fallback_receptacle}; 如果在搜索的过程中发现了{}，则将{fallback_item}放到{primary_receptacle}. 如果在搜索的过程中发现了{}，则将{fallback_item}放到{fallback_receptacle}."
        # task = f""
        
        uncertain_items = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['pickable']]
        uncertain_receptacles = [item for item in ITEM_ATTRIBUTES if ITEM_ATTRIBUTES[item]['placeable']]
        in_items = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('pickable', False)
        ]
        in_items = list(set(in_items))
        in_receptacles = [
            item.split('_')[0].lower() for item in self.items 
            if self.items[item].level > 1 and self.items[item].attributes.get('placeable', False)
        ]
        in_receptacles = list(set(in_receptacles))
        out_items = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['pickable']]
        out_receptacles = [item for item in ITEM_ATTRIBUTES if self.get_item_count(item)==0 and ITEM_ATTRIBUTES[item]['placeable']]
        
        try:
            # exist a
            if type == 1:
                primary_item  = random.choice(uncertain_items)
                primary_receptacle = random.choice(self.get_item_receptacles(primary_item) + self.get_item_receptacles_notin_items(primary_item))
                if self.get_item_count(primary_item) > 0 and self.get_item_count(primary_receptacle) > 0:
                    fallback_receptacle = random.choice([x for x in uncertain_receptacles if x!=primary_receptacle])
                    fallback_item = random.choice([x for x in uncertain_items if x !=primary_item])
                elif self.get_item_count(primary_item) > 0 and self.get_item_count(primary_receptacle) == 0:
                    fallback_receptacle = random.choice(self.get_item_receptacles(primary_item))
                    fallback_item = random.choice([x for x in uncertain_items if x !=primary_item])
                elif self.get_item_count(primary_item) == 0 and self.get_item_count(primary_receptacle) > 0:
                    fallback_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x) > 0])
                    fallback_receptacle = random.choice([x for x in uncertain_receptacles if x !=primary_receptacle])
                elif self.get_item_count(primary_item) == 0 and self.get_item_count(primary_receptacle) == 0:
                    fallback_item = random.choice(in_items)
                    fallback_receptacle = random.choice(self.get_item_receptacles(fallback_item))
                # task = f"将一个{primary_item}放到一个{primary_receptacle}上面/里面. \
                #     如果{primary_item}存在，{primary_receptacle}不存在, 则将一个{primary_item}放到一个{fallback_receptacle}上面/里面; \
                #     如果{primary_item}不存在，{primary_receptacle}存在，则将一个{fallback_item}放到一个{primary_receptacle}上面/里面. \
                #     如果两者都不存在，则将一个{fallback_item}放到一个{fallback_receptacle}上面/里面."
                task = f"Place a {primary_item} on/in a {primary_receptacle}. If the {primary_item} exists but the {primary_receptacle} does not exist, place a {primary_item} on/in a {fallback_receptacle}; If the {primary_item} does not exist but the {primary_receptacle} exists, place a {fallback_item} on/in a {primary_receptacle}. If neither exists, place a {fallback_item} on/in a {fallback_receptacle}."
                verify = f"(self.exist('{primary_item}') and self.exist('{primary_receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{primary_item}') > 0) \
                        or (self.exist('{primary_item}') and not self.exist('{primary_receptacle}') and self.count_receptacle_items('{fallback_receptacle}', '{primary_item}') > 0) \
                        or (not self.exist('{primary_item}') and self.exist('{primary_receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{fallback_item}') > 0) \
                        or (not self.exist('{primary_item}') and not self.exist('{primary_receptacle}') and self.count_receptacle_items('{fallback_receptacle}', '{fallback_item}') > 0)"
            
            # see(a)
            elif type == 2:
                primary_receptacle = random.choice(in_receptacles)
                primary_item  = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x) > 0])
                item_or_receptacle = random.choice([x for x in uncertain_receptacles + receptacle2ITEMS[primary_receptacle] if x not in [primary_item, primary_receptacle]])
                fallback_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if x!=primary_item and self.get_item_count(x) > 0])
                # task = f"将一个{primary_item}放到一个{primary_receptacle}. \
                #     在这期间如果看到了{item_or_receptacle}, 则将一个{fallback_item}放到一个{primary_receptacle}上面/里面."
                task = f"Put a {primary_item} into a {primary_receptacle}. During this process, if you see an {item_or_receptacle}, put a {fallback_item} on top of or inside a {primary_receptacle}."
                verify = f"(not self.saw('{item_or_receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{primary_item}') > 0)\
                        or (self.saw('{item_or_receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{fallback_item}') > 0)"
            
            # count(a) > n
            elif type == 3:
                primary_receptacle = random.choice(in_receptacles)
                item = random.choice(uncertain_items)
                count = self.get_item_count(item)
                n = random.randint(1, max(1, 2*count))
                if count > n:
                    fallback_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x) > 0])
                    primary_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if x!=fallback_item])
                else:
                    primary_item  = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x) > 0])
                    fallback_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if x!=primary_item])

                # task = f"将一个{primary_item}放到一个{primary_receptacle}上面/里面. \
                #     如果{item}的数量大于{n}, 则将一个{fallback_item}放到一个{primary_receptacle}上面/里面."
                task = f"Put a {primary_item} on/in a {primary_receptacle}. If the number of {item} is greater than {n}, put a {fallback_item} on/in a {primary_receptacle}."
                verify = f"(self.count('{item}')>{n} and self.count_receptacle_items('{primary_receptacle}', '{fallback_item}'))\
                        or (self.count('{item}')<={n} and self.count_receptacle_items('{primary_receptacle}', '{primary_item}'))"
            
            # visited a
            elif type == 4:
                primary_receptacle = random.choice(in_receptacles)
                primary_item, fallback_item = random.sample([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x) > 0], 2)
                receptacle = random.choice(uncertain_receptacles)
                # task = f"将一个{primary_item}放到一个{primary_receptacle}上面/里面. \
                #     在这期间如果访问了{receptacle}, 则将一个{fallback_item}放到一个{primary_receptacle}上面/里面."
                task = f"Place a {primary_item} on top of or inside a {primary_receptacle}. If {receptacle} is accessed during this period, place a {fallback_item} on top of or inside a {primary_receptacle}."
                verify = f"(self.visited('{receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{fallback_item}')) \
                        or (not self.visited('{receptacle}') and self.count_receptacle_items('{primary_receptacle}', '{primary_item}'))"
            
            # a in b
            elif type == 5:
                primary_receptacle = random.choice(in_receptacles)
                primary_item = random.choice([x for x in receptacle2ITEMS[primary_receptacle] if self.get_item_count(x)>0])
                receptacle = random.choice([x for x in in_receptacles if x!=primary_receptacle])
                item = random.choice([x for x in receptacle2ITEMS[receptacle]])
                task = f"将一个{primary_item}放到一个{primary_receptacle}上面/里面. \
                    如果{receptacle}上面/里面有{item}, 则将一个{item}放到一个{primary_receptacle}上面/里面."
                task = f"Put a {primary_item} on top of/in a {primary_receptacle}. If there is an {item} on top of/in the {receptacle}, put an {item} on top of/in a {primary_receptacle}."
                verify = f"(self.count_receptacle_items('{receptacle}', '{item}')>0 and self.count_receptacle_items('{primary_receptacle}', '{item}')>0)\
                        or (self.count_receptacle_items('{receptacle}', '{item}')==0 and self.count_receptacle_items('{primary_receptacle}', '{primary_item}')>0)"
            
            else:
                return '', ''
            return task, verify
        except Exception as e:
            return '', ''
    
    # ambiguity place
    def create_ambiguity_place_task(self):
        try:
            in_items = [
                item.split('_')[0].lower() for item in self.items 
                if self.items[item].level > 1 and self.items[item].attributes.get('pickable', False)
            ]
            in_items = list(set(in_items))
            in_receptacles = [
                item.split('_')[0].lower() for item in self.items 
                if self.items[item].level > 1 and self.items[item].attributes.get('placeable', False)
            ]
            in_receptacles = list(set(in_receptacles))
            
            item = random.choice(in_items)
            receptacle = random.choice(self.get_item_all_receptacles(item))
            precise_items = self.get_e_target(item)
            confirm_item = random.choice(precise_items)
            precise_receptacles = self.get_e_target(receptacle)
            confirm_receptacle = random.choice(precise_receptacles)
            # task = f"将{item}其放到{receptacle}上面/里面。如果你不确定具体是哪个{item}或{receptacle}，你需要通过询问来确认具体是哪个{item}或者{receptacle}."
            task = f"Put the {item} on/in the {receptacle}. If you are not sure which specific {item} or {receptacle} it is, you need to ask to confirm which specific {item} or {receptacle} it is."
            verify = f"self.item_located('{confirm_item}')=='{confirm_receptacle}'"
            if len(precise_items)>1 or len(precise_receptacles)>1:
                is_ambiguity = True
            else:
                is_ambiguity = False
            return task, verify, confirm_item, confirm_receptacle, is_ambiguity
        except Exception as e:
            return '', '', '', '', ''
    
    # miss task
    def create_miss_place_task(self, item_list, type=1):
        def split_count(total, parts):
            """将一个总数 (total) 随机分割成 N 个 (parts) 大于等于 1 的正整数。使用“隔板法”（Stars and Bars）。"""
            if parts == 1:
                return [total]
            
            # 在 1 到 total - 1 之间随机选择 parts - 1 个分割点
            # 例如：total=10, parts=3。从 [1, 2, ..., 9] 中选 2 个点。
            # 如果选中 3, 7，则结果为：3, (7-3)=4, (10-7)=3 -> [3, 4, 3]
            split_points = sorted(random.sample(range(1, total), parts - 1))

            counts = []

            # 第一个部分：从 0 到第一个分割点
            counts.append(split_points[0])

            # 中间的部分：相邻分割点之间的差值
            for i in range(parts - 2):
                counts.append(split_points[i+1] - split_points[i])

            # 最后一个部分：从最后一个分割点到总数
            counts.append(total - split_points[-1])

            return counts
        
        # 1. 不存在该物品/容器
        # 优先级访问
        # 优先级拿起
        # 优先级放置
        try:
            if type==1:
                task, reason = self.create_visited_item_task(-1)
                
            elif type==2:
                task, reason = self.create_pickup_item_task(-1)
                
            elif type==3:
                task, reason = self.create_place_item_task(-1)

            elif type==4:
                task, reason = self.create_order_visit_item_task_by_index(-1)
            
            elif type==5:
                task, reason = self.create_order_pickup_item_task_by_index(-1)
            
            elif type==6:
                task, reason = self.create_order_place_item_task_by_index(-1)
            
            # 2. 物品数量不够
            elif type==7:
                counts = [self.get_item_count(item_name) for item_name in item_list]
                receptacles = [self.get_item_precise_receptacles(item_name) for item_name in item_list]
                all_task_parts = []
                # 遍历每一种物品及其对应的数量和可用容器
                for item_name, item_total_count, available_receptacles in zip(item_list, counts, receptacles):
                    num_available_receptacles = len(available_receptacles)
                    
                    if item_total_count == 0 or num_available_receptacles == 0:
                        continue # 跳过无法操作的物品
                        
                    # 1. 决定本次任务使用的物品总数 (C)
                    # 至少用 1 个，最多用到物品的全部数量
                    count_to_use = random.randint(1, 2*item_total_count)

                    # 2. 决定本次任务使用的容器数量 (N)
                    # N 必须 <= 可用容器数，且 N 必须 <= 物品数 (确保每个容器至少分到 1 个)
                    max_n = min(count_to_use, num_available_receptacles)
                    num_receptacles_to_use = random.randint(1, max_n) 

                    # 3. 随机选择 N 个不同的容器
                    selected_receptacles = random.sample(available_receptacles, num_receptacles_to_use)

                    # 4. 将物品总数 C 分割成 N 个部分
                    item_counts = split_count(count_to_use, num_receptacles_to_use)

                    # 5. 生成该物品的任务和验证子字符串
                    current_item_task_parts = []
                    current_item_reason_parts = []
                    if count_to_use > item_total_count:
                        current_item_reason_parts.append(f"{item_name} is in insufficient quantity.")
                    
                    for item_c, receptacle_name in zip(item_counts, selected_receptacles):
                        # 任务子句：放置 X 个 item_name 到 receptacle_name
                        if self.get_item_count(receptacle_name.split('_')[0].lower())>1:
                            current_item_task_parts.append(f"Place {item_c} {item_name} on/in any one {receptacle_name.split('_')[0].lower()}")
                        else:
                            current_item_task_parts.append(f"Place {item_c} {item_name} on/in the {receptacle_name}")
                        

                    # 将该物品的所有放置指令连接起来 (例如：放置3个苹果到篮子，放置2个苹果到箱子)
                    all_task_parts.append(", ".join(current_item_task_parts))
                    
                # 最终任务字符串：用逗号连接所有物品的放置指令
                task = ", ".join(all_task_parts)
                if len(current_item_reason_parts) > 0:
                    reason = " and ".join(current_item_reason_parts)
                else:
                    return '', ''
            else:
                return '', ''
        except Exception as e:
            return '', ''
        return task, reason
        
    # interactive qa
    def create_qa_task(self, type=1):
        # 1. 某个物品在那里？
        # 2. 整栋屋子or某个房间or某个容器上/里的某个物品的数量是多少？
        # 3. 某个容器上/里的物品有哪些？
        blurred_item_list = [item.split('_')[0].lower() for item in self.items if self.items[item].level>1]
        precise_item_list = [item for item in self.items if self.items[item].level>1]
        blurred_receptacle_list = [item.split('_')[0].lower() for item in self.items 
                                  if self.items[item].level>1 and self.items[item].attributes.get('placeable', False)]
        precise_receptacle_list = [item for item in self.items 
                                  if self.items[item].level>1 and self.items[item].attributes.get('placeable', False)]
        task, answer = '', ''
        try:
            # 位置问题
            if type==1:
                item = random.choice([x for x in blurred_item_list if self.get_item_count(x)>1])
                items = self.get_e_target(item)
                answer = []
                for x in items:
                    answer.append(self.items[x].parent)
                # task = f"都有哪里存在{item}？"
                task = f"Where are there {item}?"
                answer = ", ".join(answer).strip()
            elif type==2:
                item = random.choice(precise_item_list)
                # task = f"{item}在哪里？"
                task = f"Where is {item}?"
                answer = self.items[item].parent
            elif type==3:
                # 某个具体容器上面/里面都有哪些物品？
                receptacle = random.choice(precise_receptacle_list)
                answer = [x for x in self.items[receptacle].contents]
                # task = f"{receptacle}上面/里面有哪些物品？"
                task = f"What items are on/inside the {receptacle}?"
                answer = ", ".join(answer).strip()
            
            # 对比问题
            elif type==4:
                # 有同类容器，哪个容器上面/里面的物品多？
                receptacles = [receptacle for receptacle in blurred_receptacle_list if self.get_item_count(receptacle) > 1]
                receptacle = random.choice(receptacles)
                precise_receptacles = self.get_e_target(receptacle)
                counts = [len(self.items[x].contents) for x in precise_receptacles]
                max_val = max(counts)
                indices = [i for i, v in enumerate(counts) if v == max_val]
                if len(indices)>1:
                    answer = [precise_receptacles[idx] for idx in indices]
                    answer = ", ".join(answer).strip()
                else:
                    answer = precise_receptacles[indices[0]]
                
                # task = f"哪个{receptacle}上面/里面的物品更多？"
                task = f"Which {receptacle} has more items on it/in it?"
            elif type==5:
                # 非同类容器，哪个容器上面/里面的物品多？
                # counts = [len(self.items[item].contents) for item in precise_receptacle_list]
                n = random.randint(2, min(5, len(precise_receptacle_list)))
                ids = random.sample([i for i in range(len(precise_receptacle_list))], n)
                receptacles = [precise_receptacle_list[idx] for idx in ids]
                counts = [len(self.items[item].contents) for item in receptacles]
                max_val = max(counts)
                indices = [i for i, v in enumerate(counts) if v == max_val]
                if len(indices)>1:
                    answer = [receptacles[idx] for idx in indices]
                    answer = ", ".join(answer).strip()
                else:
                    answer = receptacles[indices[0]]
                # task = f"有{receptacles}, 哪个上面/里面的物品最多？"
                task = f"There are {receptacles}; which one has the most items on it/in it?"
                
            # 数量问题
            elif type==5:
                # 所有receptacle上面/里面总共有多少item？
                receptacle = random.choice(blurred_receptacle_list)
                receptacles = self.get_e_target(receptacle)
                items = []
                for c in receptacles:
                    items.extend(list(self.items[c].contents.keys()))
                item = random.choice(items).split('_')[0]
                answer = self.count_receptacle_items(receptacle, item)
                # task = f"所有{receptacle}上面/里面总共有多少{item}?"
                task = f"How many {item} are there in total on/inside all {receptacle}?"
            elif type==6:
                # 整个房屋内的item有多少？
                item = random.choice(blurred_item_list+blurred_receptacle_list)
                # task = f"所有房间内总共有多少{item}?"
                task = f"How many {item} are there in total in all the rooms?"
                answer = self.get_item_count(item)
            elif type==7:
                # 某个房间总共有多少物品？
                rooms = [item for item in self.items if self.items[item].level==1]
                item = random.choice(blurred_item_list)
                room = random.choice(rooms)
                answer = len(self.get_room_items(room))
                # task = f"{room}内总共有多少物品?"
                task = f"How many items are there in total in the {room}?"
        
        except Exception as e:
            return '', ''
        return task, answer
    



    def random_task(self):
        try_count, max_count = 0, 10
        # visited
        task1, verify1 = self.create_visited_item_task(1)
        while (task1=='' or verify1=='') and try_count < max_count:
            try_count += 1
            task1, verify1 = self.create_visited_item_task(1)
        
        try_count = 0
        # pickup
        task2, verify2 = self.create_pickup_item_task(1)
        while (task2=='' or verify2=='') and try_count < max_count:
            try_count += 1
            task2, verify2 = self.create_pickup_item_task(1)
        
        try_count = 0
        task21, verify21 = self.create_pickup_item_task(1)
        while (task21=='' or verify21=='') and try_count < max_count:
            try_count += 1
            task21, verify21 = self.create_pickup_item_task(1)
        
        # place
        try_count = 0
        task3, verify3 = self.create_place_item_task(1)
        while (task3=='' or verify3=='') and try_count < max_count:
            try_count += 1
            task3, verify3 = self.create_place_item_task(1)
        try_count = 0
        task31, verify31 = self.create_place_item_task(1)
        while (task31=='' or verify31=='') and try_count < max_count:
            try_count += 1
            task31, verify31 = self.create_place_item_task(1)
        
        # toggle on
        try_count = 0
        task4, verify4 = self.create_toggle_on_item_task(1)
        while (task4=='' or verify4=='') and try_count < max_count:
            try_count += 1
            task4, verify4 = self.create_toggle_on_item_task(1)
        
        # toggle off
        try_count = 0
        task5, verify5 = self.create_toggle_off_item_task(1)
        while (task5=='' or verify5=='') and try_count < max_count:
            try_count += 1
            task5, verify5 = self.create_toggle_off_item_task(1)
        
        # pickup 2
        if verify2!='' and verify21!='':
            task6, verify6 = " and ".join([task2, task21]), " and ".join([verify2, verify21])
        else:
            task6, verify6 = '', ''
        # place 2
        if verify3!='' and verify31!='':
            task7, verify7 = " and ".join([task3, task31]), " and ".join([verify3, verify31])
        else:
            task7, verify7 = '', ''
        
        return random.choice([
            (task1, verify1),
            (task2, verify2),
            (task3, verify3),
            (task4, verify4),
            (task5, verify5),
            (task6, verify6),
            (task7, verify7)
        ])
    
    def l2_task(self):
        # proirity:
        pass
        
    
    def random_logic(self):
        toggled_items = [item for item in self.items if self.items[item].attributes.get('toggleable', False)]
        
        if len(toggled_items):
            toggled_item = random.choice(toggled_items)
        else:
            toggled_item = ''
        opened_items = [item for item in self.items if self.items[item].attributes.get('openable', False)]
        if len(opened_items):
            opened_item = random.choice(opened_items)
        else:
            opened_item = ''
        exist_item = random.choice([item for item in ITEM_ATTRIBUTES])
        item = random.choice([item for item in self.items])
        base_receptacle = random.choice([item for item in self.items if self.items[item].attributes.get('placeable', False)])
        if not self.get_item_precise_receptacles(item):
            receptacle = base_receptacle
        else:
            receptacle = random.choice(self.get_item_precise_receptacles(item))
        
        n = random.randint(0, max(3, self.count(item.split('_')[0].lower())*2))

        n2 = random.randint(0, max(3, self.count_receptacle_items(receptacle, item.split('_')[0].lower())*2))
        templates = [
            (f"self.exist('{exist_item}')", f"{exist_item} exists in the environment."),
            (f"self.visited('{item}')", f"The robot has visited {item}."),
            (f"self.saw('{item}')", f"The robot has seen {item}"),
            (f"self.count('{item.split('_')[0].lower()}')>{n}",f"The number of {item.split('_')[0].lower()} in the environment is greater than {n}."),
            (f"self.count_receptacle_items('{receptacle}', '{item.split('_')[0].lower()}')>{n2}", f"The number of {item.split('_')[0].lower()} in the {receptacle} is greater than {n2}.")
        ]
        if toggled_item != '':
            templates.append((f"self.toggled('{toggled_item}')", f"The status of {toggled_item} is on."))
        if opened_item != '':
            templates.append((f"self.opened('{opened_item}')", f"The status of {opened_item} is open."))
        
        return random.choice(templates)

    def random_generate_logic_expression(self, task_num, t_atom_num, l_atom_num):
        if l_atom_num ==0:
            task, verify = self.random_task()
            if verify == '' or verify == " and ":
                return '', ''
            
            while eval(verify):
                task, verify = self.random_task()
                if verify == '' or verify == " and ":
                    return '', ''
            return task, verify
            
        # 1. 随机若干个原子任务和验证函数
        tasks = {}
        flag = 0
        for i in range(task_num):
            task, verify = self.random_task()
            for k in range(t_atom_num-1):
                atom_task, atom_verify = self.random_task()
                if atom_task=='':
                    flag = flag
                op = random.choice(['AND', 'OR'])
                task = '(' + atom_task + ') ' + op + f' ({task})'
                verify = '(' + atom_verify + ') ' + op.lower() + f' ({verify})'
            tasks[task] = verify
            # 2. 随机若干个逻辑条件
            # 3. 使用 and or not 进行连接逻辑条件 生成若干个逻辑表达式和该表达式的自然语言描述
            # 4. 为每个逻辑表达式随机一个任务，使用 and 连接逻辑表达式和该任务的验证函数得到新的逻辑表达式
            logics, nls = self.random_logic()
            if flag < task_num//3 and random.random()<0.7:
                while not eval(logics):
                    logics, nls = self.random_logic()
                    for j in range(random.randint(l_atom_num//2, l_atom_num)):
                        logic, nl = self.random_logic()
                        op = random.choice(['AND', 'OR', 'AND NOT', 'OR NOT'])
                        logics = '(' + logic + ') ' + op.lower() + f' ({logics})'
                        nls = '(' + nl + ') ' + op + f' ({nls})'
                flag += 1 # 确保一定有一个分支
            else:
                for j in range(random.randint(1, max(1, l_atom_num - 1))):
                    logic, nl = self.random_logic()
                    op = random.choice(['AND', 'OR', 'AND NOT', 'OR NOT'])
                    logics = '(' + logic + ') ' + op.lower() + f' ({logics})'
                    nls = '(' + nl + ') ' + op + f' ({nls})'

            tasks[task] = '(' + logics + ') and ' + f'({tasks[task]})'

            tasks['(' + task + " IF " + nls + ')'] = tasks.pop(task)
        
        # 5. 使用 or 连接 新的逻辑表达式得到新的验证函数
        f_tasks = []
        f_verifys = []
        for task in tasks:
            f_tasks.append(task)
            f_verifys.append(tasks[task])
        random.shuffle(f_tasks)
        base_task, base_verify = self.random_task()
        for k in range(t_atom_num-1):
            atom_task, atom_verify = self.random_task()
            op = random.choice(['AND', 'OR'])
            base_task = '(' + atom_task + ') ' + op + f' ({base_task})'
            base_verify = '(' + atom_verify + ') ' + op.lower() + f' ({base_verify})'
        
        f_task, f_verify = ' OR '.join(f_tasks), ' or '.join(f_verifys)
        base_task = "If none of the above task conditions are met, " + base_task
        base_verify = '(' + base_verify + ' and ' + ' not (' + f_verify + ')' +')'
        f_verifys.append(base_verify)
        f_task += "\n" + base_task
        
        # 6. 返回最终的逻辑表达式和自然语言描述
        return f_task, ' or '.join(f_verifys)


        
        # ----任务链----
        # First t1 if l1 else t2/n
        # then t3 if l2 else t4/n
        # then t5 if l3 else t6/n
        # finally t7 if l4 else t8/n


"""LOGICWorld household robot environment (Gymnasium)."""

from __future__ import annotations

import json
import os
import random
import string
from typing import Any, Dict, List, Optional

import gymnasium as gym
from gymnasium import spaces
from openai import OpenAI

from logicworld.paths import load_scene_dataset
from logicworld.config import (
    ITEM_ATTRIBUTES,
    MAX_PICKUP_NUM,
    RECEPTACLE_TO_ITEMS as receptacle2ITEMS,
)
from logicworld.tasks import TaskGenerator

CONFIRM_SYSTEM_PROMPT = """
{query}"""
QUERY_SYSTEM_PROMPT = """
{query}"""


class Item:
    def __init__(self, name: str, level: int, parent: str, rng=None):
        self.name = name
        self.level = level    # 如果为1表示房间，2表示房间内的物品/容器，3表示在容器上/内的物品
        self.contents = {}    # 如果是容器，可以包含一些物品
        self.parent = parent  # 所属容器，用于找到上一层
        if level > 1:    
            self.attributes = self.build_item(name)
            self.status = self.build_status(self.attributes, rng)
        else:
            self.attributes = {}
            self.status = {}
            
    def __repr__(self):
        return f"<Item {self.name}, parent={self.parent}>"

    # 返回物品的可操作属性1可移动、2可开关、3可打开/关闭
    def build_item(self, name):
        name = name.split("_")[0].lower()
        return ITEM_ATTRIBUTES[name]
        
    # 如果存在2属性，记录启动/熄火状态、如果存在3属性记录打开关闭状态
    def build_status(self, attribute, rng):
        dic = {}
        def get_random_float():
            if rng is not None:
                return rng.random()
            return random.random()           
        if attribute['openable']:
            dic['opened'] = False if get_random_float() < 0.5 else True
        if attribute['toggleable']:
            dic['toggled'] = False if get_random_float() < 0.5 else True
        return dic

class Agent:
    def __init__(self, name="agent"):
        self.name = name
        self.room = None                          # 当前房间
        self.location: Optional[str] = None       # 当前房间/容器
        self.location_level: int = 0              # 0表示初始化， 1表示在某房间，2表示在某容器/物品
        self.inventory: Dict[str, Item] = {}      # 持有物品
        self.current_items: Dict[str, Item] = {}  # 当前可导航/操作的房间/容器/物品
        self.current_rooms: Dict[str, Item] = {}
        self.history: List[str] = []              # 操作记录
        self.visible_history = []
        self.visited_history = []
        self.pickup_history = []
        self.place_history = []
        self.action_history = []
    
    def record_action(self, action: str):
        self.history.append(action)

class UserAgent:
    """Optional LLM helper for ASK/ANSWER style interactions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.model = model or os.getenv("LOGICWORLD_MODEL", "deepseek-chat")
        api_key = api_key or os.getenv("LOGICWORLD_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        base_url = base_url or os.getenv("LOGICWORLD_BASE_URL", "https://api.deepseek.com/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

    def judge(self, task, response, answer):
        return False, ""

    def req(self, query, type="confirm"):
        if self.client is None:
            raise RuntimeError(
                "UserAgent requires LOGICWORLD_API_KEY or OPENAI_API_KEY to be set."
            )
        template = CONFIRM_SYSTEM_PROMPT if type == "confirm" else QUERY_SYSTEM_PROMPT
        prompt = template.format(query=query)
        messages = [{"role": "user", "content": prompt}]
        outputs = self.client.chat.completions.create(
            model=self.model,
            stream=False,
            messages=messages,
            temperature=1.0,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        dic = json.loads(outputs.choices[0].message.content)
        return dic["response"], dic["agent_state"], dic["items_state"]

    def parse_response(self, content):
        payload = json.loads(content)
        return payload["response"], payload["agent_state"], payload["items_state"]


class LOGICWorldEnv(gym.Env):
    """Text-based household robot environment with logic-conditioned tasks."""

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        house: Optional[str] = None,
        scene_data: Optional[Dict[str, Any]] = None,
        task: Optional[Dict[str, Any]] = None,
        verbose_feedback: bool = False,
    ):
        super().__init__()
        task = task or {}
        self.seed = 1234
        self.items: Dict[str, Item] = {}
        self.agent = Agent()
        self.user_agent = UserAgent()
        self.verbose_feedback = verbose_feedback
        self.actions = {
            "NAVIGATE_TO": self._navigate,
            "OPEN": self._open,
            "CLOSE": self._close,
            "PICK_UP": self._pick_up,
            "PUT_IN": self._put_in,
            "PUT_ON": self._put_on,
            "DROP": self._drop,
            "TURN_ON": self._toggle_on,
            "TURN_OFF": self._toggle_off,
            "DONE": self._done,
            "END": self._end,
            "ASK": self._ask,
            "ANSWER": self._answer,
        }

        if house is None:
            self.house = task.get("house", "house_0")
        else:
            self.house = house

        if scene_data is None:
            split = "train" if str(self.house).startswith("train") else "test"
            data = load_scene_dataset(split)
            house_idx = int(str(self.house).split("_")[-1])
            self.scene_data = data[house_idx]
            self.house_map = self._parse_map(self.scene_data)
        else:
            self.house_map = self._parse_map(scene_data)
            self.scene_data = scene_data

        self.task = task.get("task", "")
        self.answer = task.get("answer", "")
        self.verify = task.get("verify", "")
        self.reason = task.get("reason", "")
        self.confirm_item = task.get("confirm_item", "")
        self.confirm_receptacle = task.get("confirm_receptacle", "")
        self.task_type = task.get("task_type", "")
        self.goal_achieved = False
        self.steps_taken = 0
        self.max_steps = 100
        text_charset = string.printable
        self.observation_space = spaces.Text(max_length=8192, charset=text_charset)
        self.action_space = spaces.Text(max_length=256, charset=text_charset)

        self.task_generator = TaskGenerator(self)
    

    # Task generation (delegates to TaskGenerator) ---------------------------------
    def create_visited_item_task(self, type=1):
        return self.task_generator.create_visited_item_task(type)

    def create_pickup_item_task(self, type=1):
        return self.task_generator.create_pickup_item_task(type)

    def create_place_item_task(self, type=1):
        return self.task_generator.create_place_item_task(type)

    def create_toggle_on_item_task(self, type=1):
        return self.task_generator.create_toggle_on_item_task(type)

    def create_toggle_off_item_task(self, type=1):
        return self.task_generator.create_toggle_off_item_task(type)

    def create_multiple_item_place_task(self, item_list):
        return self.task_generator.create_multiple_item_place_task(item_list)

    def create_category_item_task(self, type=1):
        return self.task_generator.create_category_item_task(type)

    def create_order_visit_item_task_by_index(self, type=1):
        return self.task_generator.create_order_visit_item_task_by_index(type)

    def create_order_pickup_item_task_by_index(self, type=1):
        return self.task_generator.create_order_pickup_item_task_by_index(type)

    def create_order_place_item_task_by_index(self, type=1):
        return self.task_generator.create_order_place_item_task_by_index(type)

    def create_conditional_navigate_task(self, type=1):
        return self.task_generator.create_conditional_navigate_task(type)

    def create_conditional_pickup_task(self, type=1):
        return self.task_generator.create_conditional_pickup_task(type)

    def create_conditional_place_task(self, type=1):
        return self.task_generator.create_conditional_place_task(type)

    def create_ambiguity_place_task(self):
        return self.task_generator.create_ambiguity_place_task()

    def create_miss_place_task(self, item_list, type=1):
        return self.task_generator.create_miss_place_task(item_list, type)

    def create_qa_task(self, type=1):
        return self.task_generator.create_qa_task(type)

    def random_task(self):
        return self.task_generator.random_task()

    def l2_task(self):
        return self.task_generator.l2_task()

    def random_logic(self):
        return self.task_generator.random_logic()

    def random_generate_logic_expression(self, task_num, t_atom_num, l_atom_num):
        return self.task_generator.random_generate_logic_expression(
            task_num, t_atom_num, l_atom_num
        )

    # feedback #########################################################################################
    def _get_obs(self) -> str:
        """生成当前环境的文本观测"""
        feedback = self.feedback # 假设 self.feedback 包含上次操作的反馈
        if self.verbose_feedback:
            return "ENVIRONMENT: " + self._get_obs_natural()
        else:
            return "ENVIRONMENT: " + feedback

    def _get_obs_natural(self) -> str:
        """生成当前环境的文本观测，使用自然语言表达。"""
        # 辅助函数：将列表转换为自然语言列表，例如：['a', 'b', 'c'] -> "a, b, and c"
        def format_list(items_list):
            if not items_list:
                return "nothing"
            if len(items_list) == 1:
                return items_list[0]
            # 使用 'and' 连接最后一个元素
            return ", ".join(items_list[:-1]) + f", and {items_list[-1]}"

        # --- 1. 定位信息 (Current Location Info) ---
        room = self.agent.room
        location = self.agent.location
        # 结合房间和具体位置，避免重复
        if room != location:
            current_location_info = f"You are currently in the {room}, specifically near the {location}, "
        else:
            current_location_info = f"You are currently in the {room}, "
        
        # --- 2. 持有物品 (Inventory Info) ---
        inventory_list = list(self.agent.inventory.keys())
        held_items = format_list(inventory_list)
        inventory_info = f"carrying {held_items}, "
        
        # --- 3. 可见物品 (Visible Items Info) ---
        visible_list = list(self.agent.current_items.keys())
        visible_items = format_list(visible_list)
        
        # 根据是否有可见物品，使用不同的句子结构
        if visible_list:
            current_items_info = f"and can see {visible_items}. Some small items may be stored on or inside them, and you must get close to see them."
        else:
            current_items_info = "and don't see any other notable items nearby."
        
        # --- 4. 任务信息 (Task Info) ---
        task_info = f"USER INSTRUCTION: {self.task}"
        
        # --- 组合观测 ---
        # 假设 self.feedback 包含上次操作的结果或环境的初始描述
        
        # 组合所有信息，使用空行分隔，使其更易读
        return (
            f"{self.feedback}"
            f"{current_location_info}"
            f"{inventory_info}"
            f"{current_items_info}\n\n"
            f"{task_info}"
        )

    def _get_info(self) -> Dict[str, Any]:
        """生成额外信息"""
        return {
            "current_room": self.agent.room,
            "current_location": self.agent.location,
            "inventory": list(self.agent.inventory.keys()),
            "goal_achieved": self.goal_achieved,
            "steps_taken": self.steps_taken,
        }

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        if seed is None:
            seed = self.seed
        super().reset(seed=seed)
        # 重新初始化环境状态和Agent
        self.items = {}
        self.agent = Agent()
        self.house_map = self._parse_map(self.scene_data, rng=self.np_random) # 重新解析场景数据
        self.feedback = "" # 重置反馈信息
        self.goal_achieved = False
        self.steps_taken = 0
        self.task = options.get("task", self.task) if options else self.task
        # 设置初始位置
        rooms = [self.items[item].name for item in self.items if self.items[item].level==1]
        self.agent.room = self.np_random.choice(rooms)
        self.agent.location = self.agent.room
        self.agent.location_level = 1
        for x in list(self.items[self.agent.room].contents):
            self.agent.current_items[x] = self.items[x]
            self.agent.visible_history.append(x)
        for x in rooms:
            self.agent.current_rooms[x] = self.items[x]
        self.feedback = f"ENVIRONMENT: {self.house} initialization successful! The house's rooms are {rooms}."
        observation = self._get_obs_natural()
        info = self._get_info()
        return observation, info

    def step(self, action_str: str):
        self.steps_taken += 1
        success = False
        feedback = "Invalid action."
        reward = -0.1 # 每一步小惩罚
        # NAVIGATE_TO('LivingRoom_3')
        # 解析动作字符串
        try:
            parts = action_str.split('(', 1)
            action_name = parts[0].strip()
            args_dict = {}
            if len(parts) > 1:
                args_str = parts[1].strip(')').strip() # 'a', 'b'
                if action_name in ["ASK", "END", "ANSWER"]:
                    args_dict['target'] = args_str.strip().strip("'\"")
                else:
                    args_val = args_str.split(',')
                    if len(args_val)==1:
                        args_dict['target'] = args_val[0].strip().strip("'\"")
                    elif len(args_val)==2:
                        args_dict['target1'] = args_val[0].strip().strip("'\"")
                        args_dict['target2'] = args_val[1].strip().strip("'\"")
            
            # 调用内部方法
            if action_name in self.actions:
                action_func = self.actions[action_name]
                # 根据动作函数签名传递参数
                if action_name == "PUT_IN" or action_name == "PUT_ON":
                    success, feedback = action_func(args_dict.get('target1'), args_dict.get('target2'))
                elif action_name == "END":
                    success, feedback = action_func(args_dict.get('target')) # reason
                elif action_name == "DONE":
                    success, feedback = action_func()
                elif action_name == "ASK":
                    success, feedback = action_func(args_dict.get('target')) # question
                else: # NAVIGATE, OPEN, CLOSE, PICKUP, TURNON, TURNOFF
                    success, feedback = action_func(args_dict.get('target'))
            else:
                success, feedback = False, f"Unknown action: {action_name}"

        except Exception as e:
            success, feedback = False, f"Error processing action '{action_str}': {e}"
        
        # self.feedback = "SUCCESS" if success else "FAILED"
        self.feedback = feedback # 更新环境反馈
        self.agent.action_history.append((action_str, success, feedback))
        if success:
            reward = 1.0 # 成功执行动作的奖励
            if action_name == "DONE" and self.goal_achieved:
                reward = 10.0 # 完成任务的额外大奖励
        else:
            reward = -1.0 # 失败执行动作的惩罚

        # 判断是否结束
        is_done = (self.goal_achieved and (action_name == "DONE" and success)) or action_name == "ANSWER"
        
        truncated = self.steps_taken >= self.max_steps or action_name == "END" or (action_name == "DONE" and not is_done)

        observation = self._get_obs()
        info = self._get_info()

        return observation, reward, is_done, truncated, info

    def _build_room_map(self, scene_data):
        """从 scene_data 自动构建房间id到房间名称的映射"""
        room_map = {}
        if "rooms" in scene_data:  # 有些数据集里有rooms字段
            for room in scene_data["rooms"]:
                rid = room["id"]
                rname = room.get("roomType", rid)  # 优先取class_name
                room_map[rid] = rname
        else:
            # 如果没有rooms字段，就只保留 room|id
            # 从objects里推断
            for obj in scene_data.get("objects", []):
                parts = obj["id"].split("|")
                if len(parts) > 1 and parts[1].isdigit():
                    rid = f"room|{parts[1]}"
                    if rid not in room_map:
                        room_map[rid] = rid  # 暂时只用id
        return room_map

    def _parse_object(self, obj):
        """递归解析物体，区分容器与普通物品"""
        node = {
            "id": obj["id"],
            "assetId": obj.get("assetId", ""),
            "type": "receptacle" if obj.get("children") else "item",
            "children": []
        }
        if obj.get("children"):
            for child in obj["children"]:
                node["children"].append(self._parse_object(child))
        return node

    def _build_hierarchy(self, scene_data):
        room_map = self._build_room_map(scene_data)
        rooms = {}
        for obj in scene_data.get("objects", []):
            # 提取房间id
            obj_id = obj["id"]
            parts = obj_id.split("|")
            if len(parts) < 2:
                continue
            room_id = f"room|{parts[1]}"

            if room_id not in room_map:
                continue

            room_name = room_map[room_id]

            # 初始化房间节点
            if room_id not in rooms:
                rooms[room_id] = {"type": room_name, "receptacles": [], "items": []}

            # 判断是否为容器
            if obj.get("children"):
                rooms[room_id]["receptacles"].append(self._parse_object(obj))
            else:
                rooms[room_id]["items"].append({
                    "id": obj["id"],
                    "assetId": obj.get("assetId", ""),
                    "type": "item"
                })

        return rooms

    def _build_house_map(self, hierarchy):
        dic = {}
        items = {}
        for room in hierarchy:
            room_name = hierarchy[room]['type']
            i = 1
            room_name += "_"+str(i)
            while room_name in dic or room_name in items:
                room_name = room_name.split('_')[0]
                room_name += "_"+str(i)
                i += 1
            dic[room_name] = {}
            items[room_name] = 1
            for receptacle in hierarchy[room]['receptacles']:
                c_name = receptacle['id'].split('|')[0]
                i = 1
                c_name += "_"+str(i) 
                while c_name in dic[room_name] or c_name in items:
                    c_name = c_name.split('_')[0]
                    c_name += "_"+str(i)
                    i+=1
                items[c_name] = 1
                dic[room_name][c_name] = []
                for item in receptacle['children']:
                    i_name = item['id'].split('|')[0]
                    i = 1
                    i_name += "_"+str(i) 
                    while i_name in dic[room_name][c_name] or i_name in items:
                        i_name = i_name.split('_')[0]
                        i_name += "_"+str(i)
                        i+=1
                    items[i_name] = 1
                    dic[room_name][c_name].append(i_name)
        return dic
        # dic = {}
        # for room in hierarchy:
        #     room_name = hierarchy[room]['type']
        #     i = 1
        #     room_name += "_"+str(i)
        #     while room_name in dic:
        #         room_name = room_name.split('_')[0]
        #         room_name += "_"+str(i)
        #         i += 1
        #     dic[room_name] = {}
        #     for receptacle in hierarchy[room]['receptacles']:
        #         c_name = receptacle['id'].split('|')[0]
        #         i = 1
        #         c_name += "_"+str(i) 
        #         while c_name in dic[room_name]:
        #             c_name = c_name.split('_')[0]
        #             c_name += "_"+str(i)
        #             i+=1
        #         dic[room_name][c_name] = []
        #         for item in receptacle['children']:
        #             i_name = item['id'].split('|')[0]
        #             i = 1
        #             i_name += "_"+str(i) 
        #             while i_name in dic[room_name][c_name]:
        #                 i_name = i_name.split('_')[0]
        #                 i_name += "_"+str(i)
        #                 i+=1
        #             dic[room_name][c_name].append(i_name)
        # return dic

    def _parse_map(self, scene_data: Dict[str, Any], rng=None):
        hierarchy = self._build_hierarchy(scene_data)
        house_map = self._build_house_map(hierarchy)
        
        sorted_rooms = sorted(house_map.keys())
        for room_name in sorted_rooms:
            receptacles = house_map[room_name]
            self.items[room_name] = Item(room_name, 1, '', rng=rng)
            self.items[room_name].contents = self._parse_contents(receptacles)
            
            sorted_receptacles = sorted(receptacles.keys())
            for receptacle_name in sorted_receptacles:
                contents = receptacles[receptacle_name]
                self.items[receptacle_name] = Item(receptacle_name, 2, room_name, rng=rng)
                self.items[receptacle_name].contents = self._parse_contents(contents)
                
                sorted_items = sorted(contents)
                for item_name in sorted_items:
                    self.items[item_name] = Item(item_name, 3, parent=receptacle_name, rng=rng)
                    
        return house_map
        
        # for room_name, receptacles in house_map.items():
        #     self.items[room_name] = Item(room_name, 1, '')
        #     self.items[room_name].contents = self._parse_contents(receptacles)
        #     for receptacle_name, contents in receptacles.items():
        #         self.items[receptacle_name] = Item(receptacle_name, 2, room_name)
        #         self.items[receptacle_name].contents = self._parse_contents(contents)
        #         for item_name in contents:
        #             self.items[item_name] = Item(item_name, 3, parent=receptacle_name)
        # return house_map
    
    def _parse_contents(self, contents):
        dic = {}
        for name in contents:
            dic[name] = name
        return dic
    
    # support function #################################################################################
    def get_e_target(self, target):
        '''获取target的同类物品'''
        if '_' in target:
            name = target.split("_")[0].lower()
        else:
            name = target.lower()
        return [self.items[item].name for item in self.items if item.lower().startswith(name) and self.items[item].level>1]

    def item_located(self, target):
        if target in self.items:
            item = self.items[target]
            if item.level==1:
                return self.house
            else:
                return item.parent
        else:
            return ''
    
    def get_cur_fuzzy_matching(self, target):
        names = []
        for item in self.agent.current_items:
            if item.split('_')[0].lower() == target.lower():
            # if self.items[item].name.startswith(target):
                names.append(item)
        for item in self.agent.current_rooms:
            if item.split('_')[0].lower() == target.lower():
            # if self.items[item].name.startswith(target):
                names.append(item)
        return names
    
    def get_all_fuzzy_matching(self, target):
        names = []
        for item in self.items:
            if self.items[item].name.startswith(target):
                names.append(item)
        return names

    def get_inventory_fuzzy_matching(self, target):
        names = []
        for item in self.agent.inventory:
            if self.items[item].name.startswith(target):
                names.append(item)
        return names
    
    def get_item_contents(self, target):
        contents = []
        if '_' not in target:
            for i in range(10):
                name = target+"_"+str(i)
                if name in self.items:
                    contents.extend([x.split('_')[0] for x in self.items[name].contents.keys()])
        else:
            if target in self.items:
                contents.extend(self.items[target].contents.keys())
        return contents
    
    def get_room_items(self, room_name):
        items = []
        if '_' in room_name:
            room = self.items[room_name]
            items.extend(list(room.contents.keys()))
            for receptacle in list(room.contents.keys()):
                items.extend(list(self.items[receptacle].contents.keys()))
        else:
            rooms = [item for item in self.items if item.split('_')[0].lower()==room_name]
            for room in rooms:
                room = self.items[room]
                items.extend(list(room.contents.keys()))
                for receptacle in list(room.contents.keys()):
                    items.extend(list(self.items[receptacle].contents.keys()))
        return items

    def get_item_count(self, item_name):
        count = 0
        for item in self.items:
            if item.split('_')[0].lower() == item_name.lower():
                count += 1
        
        return count
    
    def get_item_precise_receptacles(self, item_name):
        if '_' in item_name:
            item_name = item_name.split('_')[0].lower()
        receptacles = []
        for receptacle in receptacle2ITEMS:
            if item_name in receptacle2ITEMS[receptacle]:
                for item in self.items:
                    if item.split('_')[0].lower()==receptacle:
                        receptacles.append(item)
        return receptacles
    
    def get_item_receptacles(self, item_name):
        receptacles = []
        for receptacle in receptacle2ITEMS:
            if receptacle in [item.split("_")[0].lower() for item in self.items] and item_name in receptacle2ITEMS[receptacle] and self.get_item_count(receptacle)==1:
                receptacles.append(receptacle)
        return receptacles
    
    def get_item_all_receptacles(self, item_name):
        receptacles = []
        for receptacle in receptacle2ITEMS:
            if receptacle in [item.split("_")[0].lower() for item in self.items] and item_name in receptacle2ITEMS[receptacle]:
                receptacles.append(receptacle)
        return receptacles

    def get_item_receptacles_notin_items(self, item_name):
        receptacles = []
        for receptacle in receptacle2ITEMS:
            if receptacle not in [item.split("_")[0].lower() for item in self.items] and item_name in receptacle2ITEMS[receptacle]:
                receptacles.append(receptacle)
        return receptacles
    
    # actions ###########################################################################################
    def _ask(self, question: str):
        if self.task_type != "ambiguity_place":
            return True, "USER: Any one is fine."
        
        response = "USER: " # self.user_agent.req(question)
        confirm = []
        if self.confirm_item!="" and self.confirm_item in question:
            confirm.append(self.confirm_item)
        if self.confirm_receptacle!="" and self.confirm_receptacle in question:
            confirm.append(self.confirm_receptacle)
        if len(confirm)>0:
            response += " and ".join(confirm)
        else:
            response += "None of these are. You need to search for the target item. Only when the target exists in the options you provide will I make a selection."
        # self.user_agent.req(question)
        return True, response
    
    def _answer(self, response: str):
        ans = self.user_agent.judge(self.task, response, self.answer)
        return ans
    
    def _end(self, reason: str):
        ans, feedback = self.user_agent.judge(self.task, reason, self.reason)
        return ans, feedback
    
    def _navigate(self, target: str):
        # 1. agent如果是在0级，则只可以导航到1级房间
        # 2. agent如果是在1级房间，只可以导航到2级物品/容器
        if target in self.agent.current_items or target in self.agent.current_rooms:
            item = self.items[target]
            if self.agent.location == target:
                return False, f"You are already at {target}. No need to NAVIGATE repeatedly."
            # self.agent.record_action(f"navigate to {target}")
            if item.level >= 3: # 2->3
                # pre_item = self.items[self.agent.location]
                # for child_item in pre_item.contents:
                #     self.agent.current_items.pop(child_item)                        
                self.agent.location = item.name
                self.agent.location_level = item.level
                self.agent.visited_history.append(item.name)
                return True, f"You have navigated to {item.name}."
            elif item.level==2: # 1->2 2->2 3->2
                pre_item = self.items[self.agent.location]
                if pre_item.level == 2:
                    if pre_item.attributes['placeable'] == True \
                        and (pre_item.attributes['openable'] == False or (pre_item.attributes['openable'] == True and pre_item.status["opened"]==True)):
                        for child_item in pre_item.contents:
                            self.agent.current_items.pop(child_item)

                if item.attributes['placeable'] == True:
                    if item.attributes['openable'] == True:
                        if item.status["opened"]==True:
                            for child_item in item.contents:
                                self.agent.current_items[child_item] = self.items[child_item]
                                self.agent.visible_history.append(child_item)
                            self.agent.location = item.name
                            self.agent.location_level = item.level
                            self.agent.visited_history.append(item.name)
                            return True, f"You have navigated to {item.name}, {item.name} is open, and inside it are: {list(item.contents)}."
                        else:
                            self.agent.location = item.name
                            self.agent.location_level = item.level
                            self.agent.visited_history.append(item.name)
                            return True, f"You have navigated to {item.name}, {item.name} is closed."
                    else:
                        for child_item in item.contents:
                            self.agent.current_items[child_item] = self.items[child_item]
                            self.agent.visible_history.append(child_item)
                        self.agent.location = item.name
                        self.agent.location_level = item.level
                        self.agent.visited_history.append(item.name)
                        return True, f"You have navigated to {item.name}, {item.name} has on it: {list(item.contents)}."
                else:
                    self.agent.location = item.name
                    self.agent.location_level = item.level
                    self.agent.visited_history.append(item.name)
                    return True, f"You have navigated to {item.name}."
            elif item.level==1: # 1->1 2->1 3->1
                pre_item = self.items[self.agent.location]
                pre_room = self.items[self.agent.room]
                if pre_item.level != 1:
                    for child_item in pre_item.contents:
                        if child_item in self.agent.current_items:
                            self.agent.current_items.pop(child_item)
                
                for child_item in pre_room.contents:
                    self.agent.current_items.pop(child_item)
                
                self.agent.room = item.name
                for child_item in item.contents:
                    self.agent.current_items[child_item] = self.items[child_item]
                    self.agent.visible_history.append(child_item)
                self.agent.location = item.name
                self.agent.location_level = item.level
                self.agent.visited_history.append(item.name)
                return True, f"You have navigated to {item.name}. In this room, you see: {list(item.contents)}. Some small items may be stored on or inside them, and you must get close to see them."
        elif target in self.items:
            item = self.items[target]
            if item.level >= 3:
                return False, f"{target} not found. You must first search for some possible locations where {target} might be stored."
            elif item.level == 2:
                return False, f"{target} not found. You must first search for some rooms that may have the {target}."
            elif item.level == 1: 
                return False, f"{target} not found. Please check the room name you want to navigate to."
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                item = self.items[target]
                if self.agent.location == target:
                    return False, f"You are already at {target}. No need to NAVIGATE repeatedly."
                # self.agent.record_action(f"navigate to {target}")
                if item.level >= 3: # 2->3
                    # pre_item = self.items[self.agent.location]
                    # for child_item in pre_item.contents:
                    #     self.agent.current_items.pop(child_item)                        
                    self.agent.location = item.name
                    self.agent.location_level = item.level
                    self.agent.visited_history.append(item.name)
                    return True, f"You have navigated to {item.name}."
                elif item.level == 2: # 1->2 2->2 3->2
                    pre_item = self.items[self.agent.location]
                    if pre_item.level == 2:
                        for child_item in pre_item.contents:
                            self.agent.current_items.pop(child_item)

                    if item.attributes['placeable'] == True:
                        if item.attributes['openable'] == True:
                            if item.status["opened"]==True:
                                for child_item in item.contents:
                                    self.agent.current_items[child_item] = self.items[child_item]
                                    self.agent.visible_history.append(child_item)
                                self.agent.location = item.name
                                self.agent.location_level = item.level
                                self.agent.visited_history.append(item.name)
                                return True, f"You have navigated to {item.name}, {item.name} is open, and inside it are: {list(item.contents)}" 
                            else:
                                self.agent.location = item.name
                                self.agent.location_level = item.level
                                self.agent.visited_history.append(item.name)
                                return True, f"You have navigated to {item.name}, {item.name} is closed."
                        else:
                            for child_item in item.contents:
                                self.agent.current_items[child_item] = self.items[child_item]
                                self.agent.visible_history.append(child_item)
                            self.agent.location = item.name
                            self.agent.location_level = item.level
                            self.agent.visited_history.append(item.name)
                            return True, f"You have navigated to {item.name}, {item.name} has on it: {list(item.contents)}"
                    else:
                        self.agent.location = item.name
                        self.agent.location_level = item.level
                        self.agent.visited_history.append(item.name)
                        return True, f"You have navigated to {item.name}."
                elif item.level == 1: # 1->1 2->1 3->1
                    pre_item = self.items[self.agent.location]
                    pre_room = self.items[self.agent.room]
                    if pre_item.level != 1:
                        for child_item in pre_item.contents:
                            if child_item in self.agent.current_items:
                                self.agent.current_items.pop(child_item)
                        
                    for child_item in pre_room.contents:
                        self.agent.current_items.pop(child_item)

                    self.agent.room = item.name
                    for child_item in item.contents:
                        self.agent.current_items[child_item] = self.items[child_item]
                        self.agent.visible_history.append(child_item)
                    self.agent.location = item.name
                    self.agent.location_level = item.level
                    self.agent.visited_history.append(item.name)
                    return True, f"You have navigated to {item.name}. In this room, you see: {list(item.contents)}. Some small items may be stored on or inside them, and you must get close to see them."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to navigate to."
        
        else:
            return False, f"{target} not found. Currently navigable location: {list(self.agent.current_items)}."

    def _open(self, target: str):
        # 1. agent面前有该物品，并且该物品可打开
        if target == self.agent.location:
            item = self.items[target]
            # self.agent.record_action(f"open {target}")
            if item.attributes['openable']==True:
                if item.status['opened'] == True:
                    if len(item.contents)==0:
                        return False, f"{item.name} is already open. It's empty."
                    else:
                        return False, f"{item.name} is already open. There are inside: {list(item.contents)}."
                else:
                    self.items[target].status['opened'] = True
                    if len(item.contents)==0:
                        return True, f"Successfully opened {item.name}. It's empty."
                    else:
                        # self.update_agent_current_items(item.contents)
                        for name in item.contents:
                            self.agent.current_items[name] = self.items[name]
                            self.agent.visible_history.append(name)
                        return True, f"Successfully opened {item.name}, There are inside: {list(item.contents)}."
            else:
                return False, f"{item.name} cannot be opened."
        
        elif target in self.items:
            return False, f"Please navigate to {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                if target == self.agent.location:
                    item = self.items[target]
                    # self.agent.record_action(f"open {target}")
                    if item.attributes['openable']==True:
                        if item.status['opened'] == True:
                            if len(item.contents)==0:
                                return False, f"{item.name} is already open. It's empty."
                            else:
                                return False, f"{item.name} is already open. There are inside: {list(item.contents)}."
                        else:
                            self.items[target].status['opened'] = True
                            if len(item.contents)==0:
                                return True, f"Successfully opened {item.name}. It's empty."
                            else:
                                # self.update_agent_current_items(item.contents)
                                for name in item.contents:
                                    self.agent.current_items[name] = self.items[name]
                                    self.agent.visible_history.append(name)
                                return True, f"Successfully opened {item.name}, There are inside: {list(item.contents)}."
                    else:
                        return False, f"{item.name} cannot be opened."
                else:
                    return False, f"Please navigate to {target} first."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to open."
       
        else:
            return False, f"{target} not found."

    def _close(self, target: str):
        # 1. agent面前有该物品，并且该物品可关闭
        if target == self.agent.location:
        # if target in self.agent.current_items:
            # item = self.agent.current_items[target]
            item = self.items[target]
            # self.agent.record_action(f"close {target}")
            if item.attributes['openable']==True:
                if item.status['opened'] == False:
                    return False, f"{item.name} is already closed."
                else:
                    # self.agent.current_items[target].status['opened'] = False
                    self.items[target].status['opened'] = False
                    # self.update_agent_current_items()
                    for name in item.contents:
                        self.agent.current_items.pop(name)
                    return True, f"Successfully closed {item.name}"
            else:
                return False, f"{item.name} cannot be closed."
        elif target in self.items:
            return False, f"You must navigate to {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                if target == self.agent.location:
                    item = self.items[target]
                    # self.agent.record_action(f"close {target}")
                    if item.attributes['openable']==True:
                        if item.status['opened'] == False:
                            return False, f"{item.name} is already closed"
                        else:
                            self.items[target].status['opened'] = False
                            # self.update_agent_current_items()
                            for name in item.contents:
                                self.agent.current_items.pop(name)
                            return True, f"Successfully closed {item.name}"
                    else:
                        return False, f"{item.name} cannot be closed."
                else:
                    return False, f"You must navigate to {target} first."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to close."
        else:
            return False, f"{target} not found."

    def _pick_up(self, target: str):
        # agent.location 是target的parent, 或者 agent.location就是target 或者 target和agent.location都在同一个容器里
        if target == self.agent.location \
            or (target in self.agent.current_items and self.items[target].parent == self.agent.location) \
            or (target in self.agent.current_items and self.items[self.agent.location].parent == self.items[target].parent):
            item = self.items[target]
            # self.agent.record_action(f"pickup {target}")
            if item.name in self.agent.inventory:
                return False, f"You have already picked up the {target}. No need to PICKUP repeatedly."
            if item.attributes['pickable']==True:
                if len(self.agent.inventory) >= MAX_PICKUP_NUM:
                    return False, f"Cannot pick up more items. Please drop something first. Currently carrying: {list(self.agent.inventory)}"
                else:
                    self.agent.inventory[item.name] = self.items[item.name]
                    # 更新物品位置
                    self.items[item.parent].contents.pop(item.name)
                    self.items[item.name].parent="agent"
                    self.agent.pickup_history.append(item.name)
                    return True, f"Successfully picked up {item.name}. Currently carrying: {list(self.agent.inventory)}"
            else:
                return False, f"{item.name} cannot be picked up."
        
        elif target in self.items:
            return False, f"You must navigate to {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                # self.agent.record_action(f"pickup {target}")
                if target == self.agent.location \
                    or (target in self.agent.current_items and self.items[target].parent == self.agent.location) \
                    or (target in self.agent.current_items and self.items[self.agent.location].parent == self.items[target].parent):
                    item = self.items[target]
                    if item.name in self.agent.inventory:
                        return False, f"You have already picked up the {target}. No need to PICKUP repeatedly."
                    if item.attributes['pickable']==True:
                        if len(self.agent.inventory) >= MAX_PICKUP_NUM:
                            return False, f"Cannot pick up more items. Please drop something first. Currently carrying: {list(self.agent.inventory)}"
                        else:
                            self.agent.inventory[item.name] = self.items[item.name]
                            # 更新物品位置
                            self.items[item.parent].contents.pop(item.name)
                            self.items[item.name].parent="agent"
                            self.agent.pickup_history.append(item.name)
                            return True, f"Successfully picked up {item.name}. Currently carrying: {list(self.agent.inventory)}"
                    else:
                        return False, f"{item.name} cannot be picked up."
                else:
                    return False, f"You must navigate to {target} first."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to pick up."
        
        else:
            return False, f"{target} not found."

    def _put_in(self, target1: str, target2: str):
        # self.agent.record_action(f"put {target1} in {target2}")
        # target2 是 agent.location
        if target1 in self.agent.inventory and target2==self.agent.location: # and target2 in self.agent.current_items 
            receptacle = self.items[target2]
            if receptacle.attributes['placeable'] == True:
                if receptacle.attributes['openable'] == True:
                    if receptacle.status['opened'] == True:
                        self.agent.inventory.pop(target1)
                        self.items[target1].parent=target2
                        self.items[target1].level = receptacle.level + 1
                        self.items[target2].contents[target1] = target1
                        self.agent.place_history.append((target1, target2))
                        return True, f"Successfully placed {target1} into {target2}"
                    else:
                        return False, f"{target2} is closed, please open it first."
                else:
                    self.agent.inventory.pop(target1)
                    self.items[target1].parent=target2
                    self.items[target1].level = receptacle.level+1
                    self.items[target2].contents[target1] = target1 
                    self.agent.place_history.append((target1, target2))
                    return True, f"Successfully placed {target1} on {target2}"
            else:
                return False, f"Items cannot be placed in {target2}."
        
        elif target1 not in self.agent.inventory:
            if self.get_inventory_fuzzy_matching(target1):
                matching_items = self.get_inventory_fuzzy_matching(target1)
                if len(matching_items)==1:
                    target1 = matching_items[0]
                    receptacle = self.items[target2]
                    if receptacle.attributes['placeable'] == True:
                        if receptacle.attributes['openable'] == True:
                            if receptacle.status['opened'] == True:
                                self.agent.inventory.pop(target1)
                                self.items[target1].parent=target2
                                self.items[target1].level = receptacle.level+1
                                self.items[target2].contents[target1] = target1
                                self.agent.place_history.append((target1, target2))
                                return True, f"Successfully placed {target1} into {target2}"
                            else:
                                return False, f"{target2} is closed, please open it first."
                        else:
                            self.agent.inventory.pop(target1)
                            self.items[target1].parent=target2
                            self.items[target1].level = receptacle.level+1
                            self.items[target2].contents[target1] = target1 
                            self.agent.place_history.append((target1, target2))
                            return True, f"Successfully placed {target1} on {target2}"
                    else:
                        return False, f"Items cannot be placed in {target2}."
                else:
                    return False, f"You inventory contains: {self.get_inventory_fuzzy_matching(target1)}. Please specify the item you want to place."
            else:
                return False, f"You didn't pick up {target1}. Please make sure you have {target1} in your hand first."
        
        elif target2 != self.agent.location:
            if target2.split('_')[0].lower() == self.agent.location.split('_')[0].lower():
                target2 = self.agent.location
                receptacle = self.items[target2]
                if receptacle.attributes['placeable'] == True:
                    if receptacle.attributes['openable'] == True:
                        if receptacle.status['opened'] == True:
                            self.agent.inventory.pop(target1)
                            self.items[target1].parent=target2
                            self.items[target1].level = receptacle.level+1
                            self.items[target2].contents[target1] = target1
                            self.agent.place_history.append((target1, target2))
                            return True, f"Successfully placed {target1} into {target2}"
                        else:
                            return False, f"{target2} is closed, please open it first."
                    else:
                        self.agent.inventory.pop(target1)
                        self.items[target1].parent=target2
                        self.items[target1].level = receptacle.level+1
                        self.items[target2].contents[target1] = target1 
                        self.agent.place_history.append((target1, target2))
                        return True, f"Successfully placed {target1} on {target2}"
                else:
                    return False, f"Items cannot be placed in {target2}."
            else:
                if self.get_cur_fuzzy_matching(target2):
                    matching_items = self.get_cur_fuzzy_matching(target2)
                    if len(matching_items)==1:
                        return False, f"You must navigate to {matching_items[0]} first."
                    else:
                        return False, f"Found multiple {target2}: {matching_items}. Please specify which one you want to place."
                else:
                    return False, f"You must navigate to {target2} first."
        
        else:
            return False, f"Cannot place {target1} into {target2}. Please make sure you have {target1} in your hand and navigated to {target2}."

    def _put_on(self, target1: str, target2: str):
        return self._put_in(target1, target2)
    
    def _drop(self, target: str):
        # self.agent.record_action(f"drop {target}")
        if target in self.agent.inventory:
            item = self.agent.inventory.pop(target)
            self.items[target].level = 2
            self.items[target].parent = self.agent.room
            self.items[self.agent.room].contents[target] = target # new
            if len(self.agent.inventory):
                return True, f"Successfully dropped {target}. Currently carrying: {list(self.agent.inventory)}."
            else:
                return True, f"Successfully dropped {target}. You are now carrying nothing."
        
        elif target in self.items:
            return False, f"You must pick up {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                item = self.agent.inventory.pop(target)
                self.items[target].level = 2
                self.items[target].parent = self.agent.room
                self.items[self.agent.room].contents[target] = target # new
                if len(self.agent.inventory):
                    return True, f"Successfully dropped {target}. Currently carrying: {list(self.agent.inventory)}."
                else:
                    return True, f"Successfully dropped {target}. You are now carrying nothing."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to drop."
        
        else:
            return False, f"{target} not found."

    def _toggle_on(self, target: str):
        # 关闭必须在面前或者在容器面前 target==self.agent.location or self.items[target].parent==self.agent.location
        if target == self.agent.location:
            item = self.items[target]
            if item.attributes["toggleable"]:
                if item.status['toggled'] == True:
                    return False, f"{target} is already on."
                else:
                    self.items[target].status['toggled'] = True
                    return True, f"Successfully turned on {target}."
            else:
                return False, f"{target} cannot be toggled."
        
        elif target in self.items:
            return False, f"You must navigate to {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                if target == self.agent.location:
                    item = self.items[target]
                    if item.attributes["toggleable"]:
                        if item.status['toggled'] == True:
                            return False, f"{target} is already on."
                        else:
                            self.items[target].status['toggled'] = True
                            return True, f"Successfully turned on {target}."
                    else:
                        return False, f"{target} cannot be toggled."
                else:
                    return False, f"You must navigate to {target} first."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to turn on."
        
        else:
            return False, f"{target} not found."
    
    def _toggle_off(self, target: str):
        if target == self.agent.location:
            item = self.items[target]
            if item.attributes['toggleable']:
                if item.status['toggled'] == False:
                    return False, f"{item.name} is already off."
                else:
                    self.items[target].status['toggled'] = False
                    return True, f"Successfully turned off {target}."
            else:
                return False, f"{item.name} cannot be toggled."
        
        elif target in self.items:
            return False, f"You must navigate to {target} first."
        
        elif self.get_cur_fuzzy_matching(target):
            matching_items = self.get_cur_fuzzy_matching(target)
            if len(matching_items)==1:
                target = matching_items[0]
                if target == self.agent.location:
                    item = self.items[target]
                    if item.attributes['toggleable']:
                        if item.status['toggled'] == False:
                            return False, f"{item.name} is already off."
                        else:
                            self.items[target].status['toggled'] = False
                            return True, f"Successfully turned off {target}."
                    else:
                        return False, f"{item.name} cannot be toggled."
                else:
                    return False, f"You must navigate to {target} first."
            else:
                return False, f"Found multiple {target}: {matching_items}. Please specify which one you want to turn off."
        
        else:
            return False, f"{target} not found."

    def _done(self):
        if self.verify == "":
            return False, "Error!"
        try:
            self.goal_achieved = eval(self.verify)
        except Exception as e:
            return False, f"Error! {e}"
        
        if self.goal_achieved:
            return True, "Task completed successfully!"
        else:
            return False, "Task not yet completed."
    
    # verify ###########################################################################################
    
    def verify_category_place_task(self, receptacle, category_items, item_counts):
        # for filter
        # ratio = 0
        # for count in item_counts:
        #     if count == 0:
        #         ratio += 1
        # return ratio/len(item_counts) >= 0.4

        if '_' in receptacle:
            counts = []
            for item in category_items:
                counts.append(self.count_receptacle_items(receptacle, item))
            return counts == item_counts
        else:
            receptacles = self.get_e_target(receptacle)
            for x in receptacles:
                counts = []
                for item in category_items:
                    counts.append(self.count_receptacle_items(x, item))
                if counts == item_counts:
                    return True
            return False

    def verify_order_visited_task(self, items, order):
        target_order_visited = [_ for _ in range(len(order))]
        for i, idx in enumerate(order): # 0,3 1,5 2,1 3,4 4,2
            target_order_visited[idx-1] = items[i]

        precise = '_' in target_order_visited[0]
        visited = []
        
        # for filter
        # receptacles = []
        # for item in target_order_visited:
        #     if '_' in item:
        #         receptacle = self.items[item].parent
        #         receptacles.append(receptacle)
        #     else:
        #         e_items = self.get_e_target(item)
        #         receptacle = self.items[e_items[0]].parent
        #         receptacles.append(receptacle)
        # return len(set(receptacles))/len(receptacles) >= 0.5

        for item_name in self.agent.visited_history:
            if precise:
                if item_name in target_order_visited:
                    visited.append(item_name)
            else:
                if item_name.split('_')[0].lower() in target_order_visited:
                    visited.append(item_name.split('_')[0].lower())
        
        return visited == target_order_visited

    def verify_order_pickup_task(self, items, order):
        target_order_pickup = [_ for _ in range(len(order))]
        for i, idx in enumerate(order): # 0,3 1,5 2,1 3,4 4,2
            target_order_pickup[idx-1] = items[i]
        precise = '_' in target_order_pickup[0]
        pickedup = []
        
        # for filter
        # receptacles = []
        # for item in target_order_pickup:
        #     if '_' in item:
        #         receptacle = self.items[item].parent
        #         receptacles.append(receptacle)
        #     else:
        #         e_items = self.get_e_target(item)
        #         receptacle = self.items[e_items[0]].parent
        #         receptacles.append(receptacle)
        # return len(set(receptacles))/len(receptacles) >= 0.5
        
        for item_name in self.agent.pickup_history:
            if pickedup == target_order_pickup:
                return True
            if precise:
                if item_name in target_order_pickup and item_name not in pickedup:
                    pickedup.append(item_name)
            else:
                if item_name.split('_')[0].lower() in target_order_pickup and item_name.split('_')[0].lower() not in pickedup:
                    pickedup.append(item_name.split('_')[0].lower())

        return pickedup == target_order_pickup

    def verify_order_place_task(self, items, receptacles, order):
        def check_place(a, b):
            ans = 0
            if '_' not in b[0]:
                if a[0].split('_')[0].lower()==b[0].lower():
                    ans += 1
            else:
                if a[0]==b[0]:
                    ans += 1
            if '_' not in b[1]:
                if a[1].split('_')[0].lower()==b[1].lower():
                    ans += 1
            else:
                if a[1]==b[1]:
                    ans += 1
            return ans==2
        
        # for filter
        # ratio = 0
        # for item, receptacle in zip(items, receptacles):
        #     if self.count_receptacle_items(receptacle, item) >= 1:
        #         ratio += 1
        # return ratio/len(order) >= 0.4

        place_actions = []
        for item, receptacle in zip(items, receptacles):
            place_actions.append((item, receptacle))
        
        ordered_place_actions = [ _ for _ in range(len(order))]
        for i, idx in enumerate(order):
            ordered_place_actions[idx-1] = place_actions[i]

        i, j, ans = 0, 0, 0
        while i < len(order) and j < len(self.agent.place_history):
            if check_place(self.agent.place_history[j], ordered_place_actions[i]):
                j += 1
                i += 1
                ans += 1
            else:
                j += 1
        
        return ans == len(order)

    
    # logic expression #################################################################################
    # agent
    def visited(self, item):
        if '_' in item:
            return item in self.agent.visited_history
        else:
            return item in [x.split('_')[0].lower() for x in self.agent.visited_history]
    
    def saw(self, item):
        if '_' in item:
            return item in self.agent.visible_history
        else:
            return item in [x.split('_')[0].lower() for x in self.agent.visible_history]

    def located(self, item):
        if '_' in item:
            return self.agent.location==item
        else:
            return self.agent.location.split('_')[0].lower()==item.lower()

    def hold(self, item):
        if '_' in item:
            return item in self.agent.inventory
        else:
            for x in self.agent.inventory:
                if x.split('_')[0].lower()==item.lower():
                    return True
        return False
    
    # item 
    def exist(self, item):
        if '_' in item:
            return item in self.items
        else:
            return self.get_item_count(item) > 0
    
    def count(self, item):
        if '_' in item:
            if item in self.items:
                return 1
            else:
                return 0
        else:
            return self.get_item_count(item)
    
    def opened(self, item):
        if '_' in item:
            if item not in self.items:
                return False
            if self.items[item].attributes['openable'] == True:
                return self.items[item].status['opened']
            else:
                return False
        else:
            for x in self.items:
                if x.split('_')[0].lower()==item.lower() and self.items[x].attributes['openable']:
                    return self.items[x].status['opened']
            return False

    def toggled(self, item):
        if '_' in item:
            if item not in self.items:
                return False
            if self.items[item].attributes['toggleable'] == True:
                return self.items[item].status['toggled']
            else:
                return False
        else:
            for x in self.items:
                if x.split('_')[0].lower()==item.lower() and self.items[x].attributes['toggleable']:
                    return self.items[x].status['toggled']
            return False

    def count_receptacle_items(self, receptacle, item):
        if '_' in receptacle:
            count = 0
            receptacles = [x for x in self.items if x==receptacle]
            if "_" in item:
                for c in receptacles:
                    for item_name in self.items[c].contents:
                        if item_name == item:
                            count += 1
            else:
                for c in receptacles:
                    for item_name in self.items[c].contents:
                        if item_name.split('_')[0].lower() == item:
                            count += 1
            return count
        else:
            counts = []
            
            receptacles = [x for x in self.items if x.split('_')[0].lower()==receptacle.lower()]
            if "_" in item:
                for c in receptacles:
                    count = 0
                    for item_name in self.items[c].contents:
                        if item_name == item:
                            count += 1
                    counts.append(count)
            else:
                for c in receptacles:
                    count = 0
                    for item_name in self.items[c].contents:
                        if item_name.split('_')[0].lower() == item:
                            count += 1
                    counts.append(count)
            return max(counts)
    

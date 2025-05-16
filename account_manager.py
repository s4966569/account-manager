import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import json
import os
import sys
import requests  # 导入requests库用于网络请求
import time  # 用于添加请求延迟
import threading  # 用于实现后台任务

class AccountManager:
    def __init__(self, root):
        self.root = root
        self.root.title("账号管理器")
        self.root.geometry("1400x710")  # 修改窗口高度为710
        self.root.resizable(True, True)
        
        # 数据文件路径 - 完全修改这部分
        if getattr(sys, 'frozen', False):
            # 打包后，使用exe所在目录而不是临时目录
            self.data_file = os.path.join(os.path.dirname(sys.executable), "accounts.json")
        else:
            # 开发环境，使用脚本所在目录
            self.data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.json")
        
        print(f"数据文件位置: {self.data_file}")  # 添加调试信息
        
        # 先初始化状态变量，防止加载账号时出错
        self.status_var = tk.StringVar()
        self.status_message = tk.StringVar()
        
        # 初始化赛季变量
        self.season_var = tk.StringVar(value="35")  # 默认赛季为35
        
        # 账号数据
        self.accounts = []
        
        # 段位选项
        self.rank_options = ["未定级", 
                           "青铜5", "青铜4", "青铜3", "青铜2", "青铜1", 
                           "白银5", "白银4", "白银3", "白银2", "白银1", 
                           "黄金5", "黄金4", "黄金3", "黄金2", "黄金1", 
                           "铂金5", "铂金4", "铂金3", "铂金2", "铂金1", 
                           "钻石5", "钻石4", "钻石3", "钻石2", "钻石1", 
                           "大师"]
        
        # 段位映射值（用于排序）
        self.rank_map = {rank: i for i, rank in enumerate(self.rank_options)}
        
        # 封禁时长选项 - 添加"无"选项和"自定义"选项
        self.ban_duration_options = ["无", "24小时", "72小时", "7天", "15天", "30天", "追3天", "自定义"]
        
        # 用于记住上次选择的非"无"封禁时长
        self.last_duration = "24小时"
        
        # 排序相关变量
        self.sort_column = None  # 默认不排序
        self.sort_reverse = False  # 默认升序排列
        
        # 统计信息变量
        self.stats_var = tk.StringVar(value="账号列表")
        
        # 拖放功能相关变量
        self.drag_item = None
        self.drag_source_index = None
        self.custom_order = {}  # 用于保存用户自定义的顺序
        
        # 后台任务标志
        self.background_task_running = False
        
        # 仅加载账号数据，不执行检查
        self.load_accounts_only()
        
        # 初始化赛季值
        self.initialize_season()
        
        # 创建界面
        self.create_widgets()
        
        # 更新表格显示
        self.update_treeview()
        
        # 启动时打印信息
        print("程序启动完成，准备就绪。")
        
        # 在界面显示后延迟启动后台检查任务
        self.root.after(1000, self.start_background_check)
    
    def initialize_season(self):
        """初始化赛季值，从第一个账户读取season字段"""
        if self.accounts and len(self.accounts) > 0:
            # 检查第一个账户是否有season字段
            if "season" in self.accounts[0]:
                season_num = self.accounts[0]["season"]
                print(f"从accounts.json中读取赛季: {season_num}")
                # 将赛季值设置到season_var（如果已初始化）
                if hasattr(self, 'season_var'):
                    self.season_var.set(str(season_num))
            else:
                # 没有找到season字段，写入默认值
                self.accounts[0]["season"] = 35
                self.save_accounts()
    
    def update_season(self):
        """更新游戏赛季并保存到第一个账户中"""
        try:
            # 获取输入框当前值
            season_input = self.season_var.get().strip()
            
            # 如果为空，则不进行任何操作
            if not season_input:
                return
                
            # 尝试转换为整数
            season_value = int(season_input)
            
            # 确保有至少一个账户
            if not self.accounts or len(self.accounts) == 0:
                messagebox.showwarning("警告", "没有账户，无法保存赛季值")
                return
                
            # 如果与当前值相同，则不操作
            if "season" in self.accounts[0] and self.accounts[0]["season"] == season_value:
                return
                
            # 更新第一个账户的season字段
            self.accounts[0]["season"] = season_value
            
            # 保存到文件
            if self.save_accounts():
                self.status_message.set(f"赛季已更新为: {season_value}")
                # 更新界面上的赛季显示
                self.season_var.set(str(season_value))
                self.root.after(3000, lambda: self.status_message.set(""))
        except ValueError:
            # 如果不是有效数字，恢复为原有值
            if self.accounts and len(self.accounts) > 0 and "season" in self.accounts[0]:
                self.season_var.set(str(self.accounts[0]["season"]))
            else:
                self.season_var.set("35")  # 默认值
            messagebox.showerror("错误", "请输入有效的赛季数字")
        except Exception as e:
            messagebox.showerror("错误", f"更新赛季失败: {str(e)}")
    
    def load_accounts_only(self):
        """仅从文件加载账号数据，不执行检查"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                print(f"已加载 {len(self.accounts)} 个账号")
                
                # 确保每个账号都有必要的字段
                for account in self.accounts:
                    if "level" not in account:
                        account["level"] = 0
                    if "account_id" not in account:
                        account["account_id"] = ""
                    # 确保有rank分数字段
                    if "tpp_rank_point" not in account:
                        account["tpp_rank_point"] = 0
                    if "fpp_rank_point" not in account:
                        account["fpp_rank_point"] = 0
                    # 确保有段位字段
                    if "tpp_rank" not in account:
                        account["tpp_rank"] = "未定级"
                    if "fpp_rank" not in account:
                        account["fpp_rank"] = "未定级"
                        
            except Exception as e:
                print(f"加载账号数据出错: {str(e)}")
                self.accounts = []
    
    def load_accounts(self):
        """从文件加载账号数据并检查状态"""
        self.load_accounts_only()
        # 启动时检查并更新封禁状态
        self.update_ban_status()
    
    def start_background_check(self):
        """启动后台检查任务"""
        if not self.background_task_running:
            total_accounts = len(self.accounts)
            self.status_message.set(f"正在准备检查 {total_accounts} 个账号状态...")
            # 启动后台线程执行检查
            self.background_task_running = True
            threading.Thread(target=self.background_check_task, daemon=True).start()
    
    def background_check_task(self):
        """后台线程执行账号状态检查"""
        try:
            # 执行状态更新
            updated_ban = self.update_ban_status()
            
            # 执行段位更新
            print("封禁状态检查完成，开始查询段位信息...")
            updated_rank = self.update_account_ranks()
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self.finish_background_check(updated_ban, updated_rank))
        except Exception as e:
            print(f"后台检查任务异常: {str(e)}")
            # 在主线程中更新状态
            self.root.after(0, lambda: self.status_message.set(f"检查过程出错: {str(e)}"))
            self.background_task_running = False
    
    def finish_background_check(self, updated_ban, updated_rank):
        """完成后台检查，更新界面"""
        # 更新表格
        self.update_treeview()
        
        # 更新状态信息
        if updated_ban and updated_rank:
            self.status_message.set("账号检查完成：封禁状态和段位均有更新")
        elif updated_ban:
            self.status_message.set("账号检查完成：封禁状态有更新")
        elif updated_rank:
            self.status_message.set("账号检查完成：段位有更新")
        else:
            self.status_message.set("账号检查完成：无状态变化")
        
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))
        
        # 重置后台任务标志
        self.background_task_running = False
        
        print("后台检查任务完成")
    
    def update_single_account_ui(self, idx):
        """更新单个账号的UI显示"""
        # 这个方法会在主线程中被调用
        # 找到对应的树项并更新
        items = self.tree.get_children()
        if 0 <= idx < len(items):
            item_id = items[idx]
            account = self.accounts[idx]
            
            # 获取状态和解封时间显示
            status = "❌" if account["status"] else "✅"
            unban_time_display = ""
            if account["status"] and account["unban_time"]:
                try:
                    unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                    unban_time_display = unban_time.strftime("%m-%d %H:%M")
                except:
                    unban_time_display = account["unban_time"]
            
            # 获取等级，如果等级为0则显示为空
            level_display = ""
            if "level" in account and account["level"] > 0:
                level_display = str(account["level"])
            
            # 构建TPP段位显示，结合段位和分数
            tpp_rank_display = account.get("tpp_rank", "未定级")
            tpp_rank_point = account.get("tpp_rank_point", 0)
            if tpp_rank_display != "未定级" and tpp_rank_point > 0:
                tpp_rank_display = f"{tpp_rank_display}({tpp_rank_point})"
            
            # 构建FPP段位显示，结合段位和分数
            fpp_rank_display = account.get("fpp_rank", "未定级")
            fpp_rank_point = account.get("fpp_rank_point", 0)
            if fpp_rank_display != "未定级" and fpp_rank_point > 0:
                fpp_rank_display = f"{fpp_rank_display}({fpp_rank_point})"
            
            # 更新表项
            self.tree.item(item_id, values=(
                idx + 1,
                str(account["name"]),
                str(account.get("note", "")),
                level_display,  # 没有等级或等级为0时显示为空
                fpp_rank_display,  # 使用组合的FPP段位显示
                tpp_rank_display,  # 使用组合的TPP段位显示
                status,
                unban_time_display,
                str(account.get("extended_ban", "")),
                str(account["phone"]),
                str(account.get("id", ""))
            ))
            
            # 更新统计信息
            self.update_stats_info()
    
    def check_ban_real(self, account):
        """
        检查账号的真实封禁状态
        account: 账号对象
        返回: 是否有更新
        """
        # 如果账号没有ID，不进行检查
        if not account.get("id"):
            return False
            
        # 查询网络接口
        is_banned, success, player_level, account_id = self.check_ban_status_online(account["id"])
        
        # 如果返回了有效的account_id，保存到账号对象
        if account_id:
            account["account_id"] = account_id
            print(f"账号 {account.get('name', 'unknown')} 的account_id已更新: {account_id}")
        
        # 更新账号的等级信息(无论查询封禁状态是否成功)
        level_updated = False
        if player_level > 0:
            if account.get("level", 0) != player_level:
                account["level"] = player_level
                level_updated = True
                print(f"账号 {account.get('name', 'unknown')} 等级已更新: {player_level}")
        elif player_level == 0 and "level" in account:
            # 如果API返回0但账号已有等级值，保留原有等级
            pass
        
        # 如果查询失败，仅返回等级更新状态
        if not success:
            return level_updated
            
        # 如果查询成功且账号当前状态与API状态不一致，或者仅更新了等级信息
        status_changed = account["status"] != is_banned
        if status_changed:
            account_name = account.get('name', '未命名')
            if is_banned:  # API显示已封禁，但本地状态是未封禁
                # 更新为封禁状态
                account["status"] = True
                
                # 检查当前是否有解封时间记录
                if not account.get("unban_time") or not account["unban_time"]:
                    # 没有解封时间记录，设置为24小时封禁
                    account["extended_ban"] = ""  # 不是追封，是新封禁
                    now = datetime.datetime.now()
                    unban_time = now + datetime.timedelta(hours=24)
                    account["unban_time"] = unban_time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"账号 {account_name} 被检测到封禁，已设置为封禁24小时")
                else:
                    # 有解封时间记录，视为追封
                    try:
                        # 尝试解析当前解封时间
                        current_unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                        # 检查解封时间是否已过期
                        now = datetime.datetime.now()
                        
                        # 解封时间未过期，在原解封时间基础上+2天
                        account["extended_ban"] = "追3天"
                        new_unban_time = current_unban_time + datetime.timedelta(days=2)
                        account["unban_time"] = new_unban_time.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"账号 {account_name} 被检测到追封，已延长封禁时间2天")
                    except:
                        # 解析失败，从当前时间开始计算24小时
                        account["extended_ban"] = ""  # 解析失败不作为追封
                        now = datetime.datetime.now()
                        unban_time = now + datetime.timedelta(hours=24)
                        account["unban_time"] = unban_time.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"账号 {account_name} 解封时间格式无效，重置为封禁24小时")
            else:  # API显示未封禁，但本地状态是封禁
                # 更新为未封禁状态
                account["status"] = False
                account["unban_time"] = ""
                account["extended_ban"] = ""
                print(f"账号 {account_name} 已确认解封")
                
            return True  # 状态有更新
            
        return level_updated  # 如果状态未更新，返回是否有等级更新
    
    def update_ban_status(self):
        """检查并更新账号的封禁状态，返回是否有更新"""
        print("开始执行update_ban_status()，准备检查所有账号状态...")
        current_time = datetime.datetime.now()
        status_updated = False
        api_calls_count = 0
        account_id_updated = False  # 添加标志，记录是否有account_id更新
        
        for idx, account in enumerate(self.accounts):
            account_name = account.get('name', '未命名')
            print(f"正在处理第{idx+1}个账号: {account_name}...")
            
            # 更新状态栏显示当前正在检查的账号
            self.root.after(0, lambda name=account_name, i=idx+1, total=len(self.accounts): 
                           self.status_message.set(f"正在检查账号 ({i}/{total}): {name}"))
            
            # 为每个账号初始化追封字段（如果不存在）
            if "extended_ban" not in account:
                account["extended_ban"] = ""
                
            # 为每个账号初始化account_id字段（如果不存在）
            if "account_id" not in account:
                account["account_id"] = ""
                account_id_updated = True
            
            # 首先检查本地封禁时间
            local_ban_expired = False
            if account["status"] and account["unban_time"]:
                print(f"账号 {account_name} 目前为封禁状态，解封时间: {account['unban_time']}")
                try:
                    # 检查解封时间是否已过期
                    unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                    if current_time >= unban_time:
                        print(f"账号 {account_name} 本地解封时间已过期")
                        local_ban_expired = True
                except Exception as e:
                    print(f"处理账号 {account_name} 解封时间时发生异常: {str(e)}")
                    # 日期格式无效，标记为过期以重新判断
                    local_ban_expired = True
            else:
                print(f"账号 {account_name} 目前为正常状态或无解封时间")
                
            # 对于每个有ID的账号，都调用API检查真实封禁状态
            if account.get("id"):
                print(f"账号 {account_name} ID: {account['id']}，正在查询API确认真实状态")
                
                # 准备用于API检查的账号对象
                check_account = account.copy()
                
                # 如果本地封禁已过期，在检查前将状态临时设为未封禁
                if local_ban_expired:
                    print(f"本地封禁已过期，临时标记为未封禁以进行API检查")
                    check_account["status"] = False
                
                # 进行API检查
                api_calls_count += 1
                account_updated = self.check_ban_real(check_account)
                
                # 同步等级数据（无论状态是否变化）
                if "level" in check_account and check_account.get("level", 0) > 0:
                    if account.get("level", 0) != check_account["level"]:
                        account["level"] = check_account["level"]
                        print(f"账号 {account_name} 等级已更新: {check_account['level']}")
                        # 无论状态是否变化，只要等级变化就更新UI
                        self.root.after(0, lambda i=idx: self.update_single_account_ui(i))
                        status_updated = True  # 标记为有更新，会触发保存
                
                # 同步account_id数据（无论状态是否变化）
                if "account_id" in check_account and check_account.get("account_id"):
                    old_account_id = account.get("account_id", "")
                    new_account_id = check_account.get("account_id", "")
                    if old_account_id != new_account_id:
                        account["account_id"] = new_account_id
                        print(f"同步账号 {account_name} 的account_id从 {old_account_id} 到 {new_account_id}")
                        account_id_updated = True
                
                if account_updated:
                    # API检查导致状态变化，更新原账号
                    old_status = account["status"]
                    account["status"] = check_account["status"]
                    account["unban_time"] = check_account["unban_time"]
                    account["extended_ban"] = check_account["extended_ban"]
                    status_updated = True
                    print(f"账号 {account_name} API检查后状态已更新: {'已封禁' if account['status'] else '未封禁'}")
                    
                    # 在主线程中更新UI显示
                    self.root.after(0, lambda i=idx: self.update_single_account_ui(i))
                elif local_ban_expired:
                    # API检查无更新但本地封禁已过期，设为未封禁
                    old_status = account["status"]
                    account["status"] = False
                    account["unban_time"] = ""
                    account["extended_ban"] = ""
                    status_updated = True
                    print(f"账号 {account_name} API未检测到封禁且本地封禁已过期，设为未封禁")
                    
                    # 在主线程中更新UI显示
                    self.root.after(0, lambda i=idx: self.update_single_account_ui(i))
            else:
                print(f"账号 {account_name} 无ID，仅根据本地时间判断")
                # 无ID账号，只能根据本地时间判断
                if local_ban_expired:
                    old_status = account["status"]
                    account["status"] = False
                    account["unban_time"] = ""
                    account["extended_ban"] = ""
                    status_updated = True
                    print(f"账号 {account_name} 无ID且本地封禁已过期，设为未封禁")
                    
                    # 在主线程中更新UI显示
                    self.root.after(0, lambda i=idx: self.update_single_account_ui(i))
            
            # 添加延迟以避免API请求过快
            if account.get("id"):
                print(f"添加2秒延迟，避免API请求过快")
                time.sleep(2)
        
        print(f"所有账号处理完毕，共进行了{api_calls_count}次API调用，状态更新: {status_updated}，account_id更新: {account_id_updated}")
        
        # 如果有状态更新或account_id更新，保存到文件
        if status_updated or account_id_updated:
            self.save_accounts()
            
        return status_updated
    
    def save_accounts(self):
        """保存账号数据到文件"""
        try:
            # 确保目录存在
            directory = os.path.dirname(self.data_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
            print(f"数据已成功保存到: {self.data_file}")  # 添加调试信息
            self.status_message.set(f"数据已保存")
            self.root.after(3000, lambda: self.status_message.set(""))
            return True
        except Exception as e:
            error_msg = f"保存失败: {str(e)}\n路径: {self.data_file}"
            print(error_msg)  # 添加调试信息
            messagebox.showerror("保存错误", error_msg)
            self.status_message.set("数据保存失败")
            return False
    
    def create_widgets(self):
        """创建界面元素"""
        # 创建左侧表格
        self.create_account_list()
        
        # 创建右侧表单
        self.create_account_form()
        
        # 创建刷新按钮
        self.refresh_btn = ttk.Button(self.root, text="刷新状态", command=self.refresh_ban_status, width=10)
        self.refresh_btn.place(x=550, y=0)
        
        # 添加游戏赛季控件（位于刷新状态按钮后面）
        ttk.Label(self.root, text="游戏赛季:").place(x=700, y=5)
        season_entry = ttk.Entry(self.root, textvariable=self.season_var, width=5)
        season_entry.place(x=760, y=2)
        # 绑定回车键事件，使按回车键时触发update_season并将焦点转移到主窗口
        season_entry.bind("<Return>", lambda event: [self.update_season(), self.root.focus_set()])
        
        # 创建状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_message, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_account_list(self):
        """创建账号列表"""
        # 创建Frame - 调整宽度
        self.list_frame = ttk.LabelFrame(self.root, text="账号列表")
        self.list_frame.place(x=10, y=10, width=950, height=680)  # 增加高度
        
        # 创建Treeview - 添加level列在note后面
        columns = ("number", "name", "note", "level", "fpp_rank", "tpp_rank", "status", "unban_time", "extended_ban", "phone", "id")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", selectmode="browse")
        
        # 配置高亮样式
        self.tree.tag_configure('highlight', background='#ECECEC')
        
        # 设置列标题，重新添加排序功能
        self.tree.heading("number", text="序号")
        self.tree.heading("name", text="账号名称")
        self.tree.heading("note", text="备注")  # 移除点击排序命令
        self.tree.heading("level", text="等级", command=lambda: self.force_sort("level"))  # 添加等级列
        self.tree.heading("fpp_rank", text="FPP段位", command=lambda: self.force_sort("fpp_rank"))
        self.tree.heading("tpp_rank", text="TPP段位", command=lambda: self.force_sort("tpp_rank"))
        self.tree.heading("status", text="状态", command=lambda: self.force_sort("status"))
        self.tree.heading("unban_time", text="解封时间", command=lambda: self.force_sort("unban_time"))
        self.tree.heading("extended_ban", text="追封")
        self.tree.heading("phone", text="ARS", command=lambda: self.force_sort("phone"))
        self.tree.heading("id", text="ID")
        
        # 调整列宽以适应表格总宽度
        self.tree.column("number", width=40)  # 序号列窄一些
        self.tree.column("name", width=100)
        self.tree.column("note", width=140)  # 略微减小备注列宽度
        self.tree.column("level", width=50)  # 等级列宽
        self.tree.column("fpp_rank", width=80)
        self.tree.column("tpp_rank", width=80)
        self.tree.column("status", width=60)
        self.tree.column("unban_time", width=135)
        self.tree.column("extended_ban", width=60)  # 追封列宽
        self.tree.column("phone", width=90)  # 略微减小ARS列宽度
        self.tree.column("id", width=75)  # 略微减小ID列宽
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定双击事件以复制内容
        self.tree.bind("<Double-1>", self.copy_cell_content)
        
        # 绑定单击事件以选择账号
        self.tree.bind("<<TreeviewSelect>>", self.on_account_selected)
        
        # 绑定拖放相关事件
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_release)
    
    def create_account_form(self):
        """创建账号表单"""
        # 创建Frame - 右移表单
        form_frame = ttk.LabelFrame(self.root, text="账号详情")
        form_frame.place(x=970, y=10, width=420, height=680)  # 增加高度
        
        # 账号名称
        ttk.Label(form_frame, text="账号名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=34).grid(row=0, column=1, padx=10, pady=10)
        
        # 等级
        ttk.Label(form_frame, text="等级:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.level_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.level_var, width=34, state="readonly").grid(row=1, column=1, padx=10, pady=10)
        
        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.password_var, width=34).grid(row=2, column=1, padx=10, pady=10)
        
        # TPP段位
        ttk.Label(form_frame, text="TPP段位:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.tpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.tpp_rank_var, values=self.rank_options, width=31, state="readonly").grid(row=3, column=1, padx=10, pady=10)
        
        # FPP段位
        ttk.Label(form_frame, text="FPP段位:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.fpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.fpp_rank_var, values=self.rank_options, width=31, state="readonly").grid(row=4, column=1, padx=10, pady=10)
        
        # 手机号
        ttk.Label(form_frame, text="ARS:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.phone_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.phone_var, width=34).grid(row=5, column=1, padx=10, pady=10)
        
        # ID
        ttk.Label(form_frame, text="ID:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.id_var, width=34).grid(row=6, column=1, padx=10, pady=10)
        
        # 当前状态
        ttk.Label(form_frame, text="封禁状态:").grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.status_var = tk.BooleanVar()
        # 添加跟踪变量变化的回调
        self.status_var.trace_add("write", self.on_status_changed)
        
        status_frame = ttk.Frame(form_frame)
        status_frame.grid(row=7, column=1, padx=10, pady=10, sticky="w")
        ttk.Radiobutton(status_frame, text="正常 ✅", variable=self.status_var, value=False).pack(side="left")
        ttk.Radiobutton(status_frame, text="封禁 ❌", variable=self.status_var, value=True).pack(side="left", padx=10)
        
        # 解封时间
        ttk.Label(form_frame, text="解封时间:").grid(row=8, column=0, padx=10, pady=10, sticky="w")
        self.unban_time_var = tk.StringVar()
        # 添加跟踪变量变化的回调，用于检测手动修改
        self.unban_time_var.trace_add("write", self.on_unban_time_changed)
        ttk.Entry(form_frame, textvariable=self.unban_time_var, width=34).grid(row=8, column=1, padx=10, pady=10)
        
        # 追封状态
        ttk.Label(form_frame, text="追封状态:").grid(row=9, column=0, padx=10, pady=10, sticky="w")
        self.extended_ban_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.extended_ban_var, width=34, state="readonly").grid(row=9, column=1, padx=10, pady=10)
        
        # 标记封禁 - 改为RadioButton横向排列
        ttk.Label(form_frame, text="封禁时长:").grid(row=10, column=0, padx=10, pady=10, sticky="w")
        ban_frame = ttk.Frame(form_frame)
        ban_frame.grid(row=10, column=1, padx=10, pady=10, sticky="w")
        
        # 创建两行RadioButton，每行4个
        ban_row1 = ttk.Frame(ban_frame)
        ban_row1.pack(fill="x", pady=2)
        ban_row2 = ttk.Frame(ban_frame)
        ban_row2.pack(fill="x", pady=2)
        
        self.ban_duration_var = tk.StringVar(value="无")  # 默认选中"无"选项
        # 添加跟踪变量变化的回调
        self.ban_duration_var.trace_add("write", self.on_duration_changed)
        
        # 存储RadioButton引用，方便后续控制
        self.duration_radios = {}
        
        # 第一行放4个选项
        for i, duration in enumerate(self.ban_duration_options[:4]):
            radio = ttk.Radiobutton(ban_row1, text=duration, variable=self.ban_duration_var, value=duration)
            radio.pack(side="left", padx=5)
            self.duration_radios[duration] = radio
        
        # 第二行放4个选项
        for duration in self.ban_duration_options[4:]:
            radio = ttk.Radiobutton(ban_row2, text=duration, variable=self.ban_duration_var, value=duration)
            radio.pack(side="left", padx=5)
            self.duration_radios[duration] = radio
            
        # 初始化时禁用"追3天"选项
        self.duration_radios["追3天"].configure(state="disabled")
        
        # 添加监听器，使status_var和unban_time_var变化时更新"追3天"按钮状态
        self.status_var.trace_add("write", self.update_extend_button_state)
        self.unban_time_var.trace_add("write", self.update_extend_button_state)
        
        # 备注 - 改为3行高的文本框
        ttk.Label(form_frame, text="备注:").grid(row=11, column=0, padx=10, pady=10, sticky="nw")
        self.note_text = tk.Text(form_frame, width=34, height=3)
        self.note_text.grid(row=11, column=1, padx=10, pady=10, sticky="w")
        
        # 按钮区域
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=12, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="新建", command=self.clear_form).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="保存", command=self.save_account).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="删除", command=self.delete_account).pack(side="left", padx=10)
    
    def copy_cell_content(self, event):
        """根据双击的列复制相应内容"""
        # 获取点击的项目和列
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
            
        column = self.tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1  # 将#1, #2等转换为0, 1等索引
        
        # 获取点击的行
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # 获取行中的值
        values = self.tree.item(item, "values")
        if not values or column_index >= len(values):
            return
            
        # 获取列名
        column_name = self.tree["columns"][column_index]
        
        # 只允许特定列可复制：账号名称、ARS、ID
        allowed_columns = ["name", "phone", "id"]
        if column_name not in allowed_columns:
            return
            
        # 复制相应内容
        content = values[column_index]
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            
            # 显示提示信息
            column_display_name = self.tree.heading(column_name, option="text")
            if column_display_name.endswith(" ▲") or column_display_name.endswith(" ▼"):
                column_display_name = column_display_name[:-2]
                
            self.status_message.set(f"已复制{column_display_name}：{content}")
            self.root.after(3000, lambda: self.status_message.set(""))
    
    def clear_form(self):
        """清空表单"""
        self.current_account_id = None
        self.name_var.set("")
        self.level_var.set("")  # 清空等级
        self.password_var.set("")
        self.tpp_rank_var.set("")
        self.fpp_rank_var.set("")
        self.phone_var.set("")
        self.id_var.set("")  # 清空ID
        self.status_var.set(False)
        self.unban_time_var.set("")
        self.extended_ban_var.set("")  # 清空追封状态
        self.ban_duration_var.set("无")  # 默认为"无"
        
        # 清空备注文本框
        self.note_text.delete("1.0", tk.END)
        
        # 注意：不清空赛季值，保持当前设置
        
        # 取消选择
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection()[0])
    
    def on_unban_time_changed(self, *args):
        """当解封时间手动修改时触发"""
        # 只有在封禁状态时才执行
        if not self.status_var.get():
            return
            
        # 获取当前解封时间
        unban_time_str = self.unban_time_var.get()
        if not unban_time_str:
            return
            
        # 检查是否与标准时长匹配
        try:
            unban_time = datetime.datetime.strptime(unban_time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            diff = (unban_time - now).total_seconds() / 3600  # 差异小时数
            
            # 检查与标准时长的差异，允许5分钟的误差
            if abs(diff - 24) < 0.1:
                self.ban_duration_var.set("24小时")
            elif abs(diff - 72) < 0.1:
                self.ban_duration_var.set("72小时")
            elif abs(diff - 7*24) < 0.1:
                self.ban_duration_var.set("7天")
            elif abs(diff - 15*24) < 0.1:
                self.ban_duration_var.set("15天")
            elif abs(diff - 30*24) < 0.1:
                self.ban_duration_var.set("30天")
            else:
                # 不匹配标准时长，设为自定义
                self.ban_duration_var.set("自定义")
        except:
            # 日期格式无效或其他错误，设为自定义
            self.ban_duration_var.set("自定义")
            
        # 更新"追3天"按钮状态
        self.update_extend_button_state()
    
    def on_status_changed(self, *args):
        """当封禁状态变化时触发"""
        if self.status_var.get():  # 如果选择了封禁状态
            # 如果当前选择的是"无"，则自动切换到上次选择的时长
            if self.ban_duration_var.get() == "无":
                self.ban_duration_var.set(self.last_duration)
            self.calculate_unban_time()
        else:  # 如果选择了正常状态
            # 自动设置封禁时长为"无"
            self.ban_duration_var.set("无")
            # 清空解封时间
            self.unban_time_var.set("")
            # 清空追封标记
            self.extended_ban_var.set("")
        
        # 更新"追3天"按钮状态
        self.update_extend_button_state()
    
    def on_duration_changed(self, *args):
        """当封禁时长变化时触发"""
        duration = self.ban_duration_var.get()
        
        if duration == "无":
            # 选择"无"时，状态设为正常
            self.status_var.set(False)
            # 清空解封时间和追封标记
            self.unban_time_var.set("")
            self.extended_ban_var.set("")
        elif duration == "追3天":
            # 选择"追3天"时，处理追加封禁
            self.status_var.set(True)  # 确保设为封禁状态
            self.extended_ban_var.set("追3天")  # 设置追封标记
            
            # 获取当前解封时间
            current_unban_time_str = self.unban_time_var.get()
            now = datetime.datetime.now()
            
            if current_unban_time_str:
                try:
                    # 尝试解析当前解封时间
                    current_unban_time = datetime.datetime.strptime(current_unban_time_str, "%Y-%m-%d %H:%M:%S")
                    
                    # 计算与当前时间的差值（小时）
                    hours_from_now = (current_unban_time - now).total_seconds() / 3600
                    
                    if hours_from_now <= 0:
                        # 已过期，从当前时间开始计算3天
                        new_unban_time = now + datetime.timedelta(days=3)
                    else:
                        # 在当前解封时间基础上追加2天（因为原来是1天，加2天后就是3天）
                        new_unban_time = current_unban_time + datetime.timedelta(days=2)
                            
                    # 设置新的解封时间
                    self.unban_time_var.set(new_unban_time.strftime("%Y-%m-%d %H:%M:%S"))
                    
                    # 操作完成后，自动将选项设为"72小时"
                    self.root.after(100, lambda: self.ban_duration_var.set("72小时"))
                    
                except Exception as e:
                    # 解析失败，从当前时间开始计算3天
                    new_unban_time = now + datetime.timedelta(days=3)
                    self.unban_time_var.set(new_unban_time.strftime("%Y-%m-%d %H:%M:%S"))
                    # 操作完成后，自动将选项设为"72小时"
                    self.root.after(100, lambda: self.ban_duration_var.set("72小时"))
            else:
                # 没有当前解封时间，从当前时间开始计算3天
                new_unban_time = now + datetime.timedelta(days=3)
                self.unban_time_var.set(new_unban_time.strftime("%Y-%m-%d %H:%M:%S"))
                # 操作完成后，自动将选项设为"72小时"
                self.root.after(100, lambda: self.ban_duration_var.set("72小时"))
        elif duration == "自定义":
            # 选择"自定义"时，状态设为封禁，但不修改解封时间
            self.status_var.set(True)
            # 如果没有解封时间，设置一个默认的（24小时后）
            if not self.unban_time_var.get():
                unban_time = datetime.datetime.now() + datetime.timedelta(hours=24)
                self.unban_time_var.set(unban_time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            # 记住当前非"无"和非"自定义"选项
            self.last_duration = duration
            # 选择标准时长时，状态设为封禁
            self.status_var.set(True)
            # 清空追封标记
            self.extended_ban_var.set("")
            # 计算解封时间
            self.calculate_unban_time()
    
    def calculate_unban_time(self):
        """根据封禁时长计算解封时间"""
        duration = self.ban_duration_var.get()
        if not duration or duration == "无" or duration == "自定义":
            return
            
        # 计算解封时间
        now = datetime.datetime.now()
        
        if duration == "24小时":
            unban_time = now + datetime.timedelta(hours=24)
        elif duration == "72小时":
            unban_time = now + datetime.timedelta(hours=72)
        elif duration == "7天":
            unban_time = now + datetime.timedelta(days=7)
        elif duration == "15天":
            unban_time = now + datetime.timedelta(days=15)
        elif duration == "30天":
            unban_time = now + datetime.timedelta(days=30)
        
        # 设置解封时间
        self.unban_time_var.set(unban_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 更新"追3天"按钮状态
        self.update_extend_button_state()
    
    def save_account(self):
        """保存账号信息"""
        name = str(self.name_var.get()).strip()
        
        if not name:
            messagebox.showwarning("警告", "账号名称不能为空")
            return
        
        # 确保如果是封禁状态，强制计算一次解封时间
        if self.status_var.get():
            self.calculate_unban_time()
        
        # 获取备注文本
        note_text = self.note_text.get("1.0", tk.END).strip()
        
        # 获取等级（如果为空，则设为0）
        try:
            level = int(self.level_var.get()) if self.level_var.get() else 0
        except ValueError:
            level = 0
        
        # 初始化account_id字段为空字符串
        account_id = ""
        
        # 如果是更新现有账号，检查名称是否变更
        if hasattr(self, 'current_account_id') and self.current_account_id is not None:
            # 如果修改现有账号，检查名称是否变更
            old_name = self.accounts[self.current_account_id].get("name", "")
            # 如果名称没有变化，保留原来的account_id值
            if old_name == name:
                account_id = self.accounts[self.current_account_id].get("account_id", "")
                print(f"账号名称未变更，保留原有account_id: {account_id}")
            else:
                print(f"账号名称已变更: {old_name} -> {name}，清空account_id")
        
        account = {
            "name": name,
            "password": self.password_var.get(),
            "tpp_rank": self.tpp_rank_var.get(),
            "fpp_rank": self.fpp_rank_var.get(),
            "phone": self.phone_var.get(),
            "id": self.id_var.get(),
            "status": self.status_var.get(),
            "unban_time": self.unban_time_var.get(),
            "extended_ban": self.extended_ban_var.get(),
            "level": level,
            "note": note_text,
            "account_id": account_id
        }
        
        if hasattr(self, 'current_account_id') and self.current_account_id is not None:
            # 更新现有账号
            self.accounts[self.current_account_id] = account
        else:
            # 添加新账号
            # 如果未排序状态，新账号添加到列表顶部
            if not self.sort_column:
                self.accounts.insert(0, account)
                # 更新自定义顺序
                self.save_custom_order()
            else:
                # 处于排序状态，直接添加到列表末尾，排序会在update_treeview中进行
                self.accounts.append(account)
        
        # 保存到文件
        self.save_accounts()
        
        # 更新表格
        self.update_treeview()
        
        # 清空表单
        self.clear_form()
    
    def delete_account(self):
        """删除账号"""
        if not hasattr(self, 'current_account_id') or self.current_account_id is None:
            messagebox.showwarning("警告", "请先选择要删除的账号")
            return
        
        # 获取当前选中的树形视图项
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的账号")
            return
        
        # 获取选中项的名称
        item = self.tree.item(selection[0])
        values = item["values"]
        selected_name = str(values[1])
        
        # 再次确认current_account_id指向的是正确的账号
        if str(self.accounts[self.current_account_id]["name"]) != selected_name:
            messagebox.showerror("错误", "账号选择不匹配，请重新选择要删除的账号")
            return
        
        if messagebox.askyesno("确认", f"确定要删除账号 '{selected_name}' 吗？"):
            del self.accounts[self.current_account_id]
            self.save_accounts()
            self.update_treeview()
            self.clear_form()
    
    def update_treeview(self):
        """更新账号列表"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 计算统计数据
        total_accounts = len(self.accounts)
        banned_accounts = sum(1 for account in self.accounts if account["status"])
        unbanned_accounts = total_accounts - banned_accounts
        extended_bans = sum(1 for account in self.accounts if account.get("extended_ban") == "追3天")
        accounts_with_level = sum(1 for account in self.accounts if account.get("level", 0) > 0)
        
        # 更新统计信息
        stats_text = f"账号列表 (共{total_accounts}个账号，封禁中{banned_accounts}个，未封禁{unbanned_accounts}个，追封{extended_bans}个)"
        self.list_frame.configure(text=stats_text)
        
        # 排序账号数据
        sorted_accounts = self.accounts.copy()
        
        # 检查是否所有账号都是未封禁状态
        all_unbanned = all(not account["status"] for account in sorted_accounts)
        
        if self.sort_column:
            # 如果有排序列，则根据排序列排序
            if self.sort_column == "tpp_rank":
                # 按TPP段位排序
                def tpp_rank_key(account):
                    # 获取段位名称
                    basic_rank = account.get("tpp_rank", "未定级")
                    
                    # 首先按段位级别排序
                    rank_level = self.rank_map.get(basic_rank, 0)
                    # 如果段位相同，则按分数排序
                    rank_point = account.get("tpp_rank_point", 0)
                    return (rank_level, -rank_point)  # 分数高的排前面，所以用负值
                
                sorted_accounts.sort(
                    key=tpp_rank_key,
                    reverse=self.sort_reverse
                )
            elif self.sort_column == "fpp_rank":
                # 按FPP段位排序
                def fpp_rank_key(account):
                    # 获取段位名称
                    basic_rank = account.get("fpp_rank", "未定级")
                    
                    # 首先按段位级别排序
                    rank_level = self.rank_map.get(basic_rank, 0)
                    # 如果段位相同，则按分数排序
                    rank_point = account.get("fpp_rank_point", 0)
                    return (rank_level, -rank_point)  # 分数高的排前面，所以用负值
                
                sorted_accounts.sort(
                    key=fpp_rank_key,
                    reverse=self.sort_reverse
                )
            elif self.sort_column == "status":
                # 按状态排序（True表示封禁，False表示正常）
                sorted_accounts.sort(
                    key=lambda x: x["status"],
                    reverse=self.sort_reverse
                )
            elif self.sort_column == "phone":
                # 按ARS(手机号)排序
                sorted_accounts.sort(
                    key=lambda x: str(x.get("phone", "")),
                    reverse=self.sort_reverse
                )
            elif self.sort_column == "level":
                # 按等级排序
                sorted_accounts.sort(
                    key=lambda x: int(x.get("level", 0)) if x.get("level", 0) > 0 else -1,
                    reverse=self.sort_reverse
                )
            elif self.sort_column == "unban_time":
                # 按解封时间排序
                def unban_time_key(account):
                    # 首先按照是否封禁分组
                    if not account["status"]:  # 未封禁
                        # 未封禁的账号始终排在封禁账号的前面
                        return (0, datetime.datetime.min)
                    
                    # 已封禁的账号，按解封时间排序
                    unban_time = account["unban_time"]
                    if not unban_time:
                        return (1, datetime.datetime.max)  # 没有解封时间但已封禁
                    
                    try:
                        return (1, datetime.datetime.strptime(unban_time, "%Y-%m-%d %H:%M:%S"))
                    except:
                        # 解析失败的
                        return (1, datetime.datetime.max)
                
                sorted_accounts.sort(
                    key=unban_time_key,
                    reverse=self.sort_reverse
                )
        
        # 添加账号数据，包括ID列和追封列
        for i, account in enumerate(sorted_accounts):
            status = "❌" if account["status"] else "✅"
            # 确保账号对象有备注字段、ID字段和追封字段
            note = account.get("note", "")
            account_id = account.get("id", "")
            extended_ban = account.get("extended_ban", "")
            
            # 获取等级，如果等级为0则显示为空
            level_display = ""
            if "level" in account and account["level"] > 0:
                level_display = str(account["level"])
            
            # 格式化解封时间为简略格式
            unban_time_display = ""
            if account["status"] and account["unban_time"]:
                try:
                    unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                    unban_time_display = unban_time.strftime("%m-%d %H:%M")
                except:
                    unban_time_display = account["unban_time"]
            
            # 构建TPP段位显示，结合段位和分数
            tpp_rank_display = account.get("tpp_rank", "未定级")
            tpp_rank_point = account.get("tpp_rank_point", 0)
            if tpp_rank_display != "未定级" and tpp_rank_point > 0:
                tpp_rank_display = f"{tpp_rank_display}({tpp_rank_point})"
            
            # 构建FPP段位显示，结合段位和分数
            fpp_rank_display = account.get("fpp_rank", "未定级")
            fpp_rank_point = account.get("fpp_rank_point", 0)
            if fpp_rank_display != "未定级" and fpp_rank_point > 0:
                fpp_rank_display = f"{fpp_rank_display}({fpp_rank_point})"
            
            # 插入数据的顺序需要与列顺序一致
            self.tree.insert("", "end", values=(
                i + 1,  # 序号从1开始
                str(account["name"]),
                str(note),
                level_display,  # 等级列，没有值时为空
                fpp_rank_display,  # 使用组合的FPP段位显示
                tpp_rank_display,  # 使用组合的TPP段位显示
                status,
                unban_time_display,
                str(extended_ban),  # 追封列
                str(account["phone"]),
                str(account_id)
            ))
        
        # 更新统计信息
        self.update_stats_info()
    
    def on_account_selected(self, event):
        """选中账号时的处理"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        values = item["values"]
        selected_name = str(values[1])  # 确保selected_name是字符串类型
        
        # 查找对应的账号
        for i, account in enumerate(self.accounts):
            if str(account["name"]) == selected_name:  # 确保比较时两边都是字符串
                self.current_account_id = i
                self.name_var.set(account["name"])
                
                # 设置等级，如果等级为0则显示为空
                level_value = ""
                if "level" in account and account["level"] > 0:
                    level_value = str(account["level"])
                self.level_var.set(level_value)  # 设置等级
                self.password_var.set(account["password"])
                self.tpp_rank_var.set(account["tpp_rank"])
                self.fpp_rank_var.set(account["fpp_rank"])
                self.phone_var.set(account["phone"])
                self.id_var.set(account.get("id", ""))  # 设置ID
                self.status_var.set(account["status"])
                self.unban_time_var.set(account["unban_time"])
                self.extended_ban_var.set(account.get("extended_ban", ""))  # 设置追封状态
                
                # 设置备注（如果有）- 使用Text控件
                self.note_text.delete("1.0", tk.END)
                if "note" in account and account["note"]:
                    self.note_text.insert("1.0", account["note"])
                
                # 根据状态和解封时间设置封禁时长
                if not account["status"]:
                    self.ban_duration_var.set("无")
                elif account["unban_time"]:
                    # 尝试根据解封时间推断封禁时长
                    try:
                        unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                        now = datetime.datetime.now()
                        delta = unban_time - now
                        hours = delta.total_seconds() / 3600
                        
                        # 检查是否匹配标准时长
                        if hours <= 0:
                            self.ban_duration_var.set("无")
                        elif abs(hours - 24) < 1:
                            self.ban_duration_var.set("24小时")
                        elif abs(hours - 72) < 1:
                            self.ban_duration_var.set("72小时")
                        elif abs(hours - 7*24) < 3:
                            self.ban_duration_var.set("7天")
                        elif abs(hours - 15*24) < 5:
                            self.ban_duration_var.set("15天")
                        elif abs(hours - 30*24) < 10:
                            self.ban_duration_var.set("30天")
                        else:
                            self.ban_duration_var.set("自定义")
                    except:
                        # 如果解析失败，使用自定义
                        self.ban_duration_var.set("自定义")
                else:
                    self.ban_duration_var.set("24小时")
                
                # 确保season_var已更新为当前设置的赛季值（从第一个账户读取）
                if self.accounts and len(self.accounts) > 0 and "season" in self.accounts[0]:
                    self.season_var.set(str(self.accounts[0]["season"]))
                
                break
                
        # 更新"追3天"按钮状态
        self.update_extend_button_state()
    
    def treeview_sort_column(self, column):
        """对treeview的列进行排序"""
        # 如果点击的是当前排序列，则切换排序方向
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # 排序后更新treeview
        self.update_treeview()
        
        # 显示排序状态
        direction = "降序" if self.sort_reverse else "升序"
        column_name = {
            "tpp_rank": "TPP段位",
            "fpp_rank": "FPP段位",
            "status": "状态",
            "unban_time": "解封时间",
            "phone": "ARS",
            "note": "备注"
        }.get(column, column)
        self.status_message.set(f"已按{column_name}进行{direction}排序")
        
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))

    def force_sort(self, column):
        """强制对指定列进行排序"""
        # 如果点击的是当前排序列，则切换排序方向
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            # 如果点击的是新列，设置为该列的升序排序
            self.sort_column = column
            self.sort_reverse = False
        
        # 更新列标题显示排序方向
        for col in self.tree["columns"]:
            # 先清除所有列的排序标记
            current_text = self.tree.heading(col, option="text")
            if current_text.endswith(" ▲") or current_text.endswith(" ▼"):
                self.tree.heading(col, text=current_text[:-2])
        
        # 为当前排序列添加方向标记
        current_text = self.tree.heading(column, option="text")
        direction_mark = " ▼" if self.sort_reverse else " ▲"
        self.tree.heading(column, text=current_text + direction_mark)
        
        # 执行排序
        self.update_treeview()
        
        # 显示排序状态
        column_name = {
            "tpp_rank": "TPP段位",
            "fpp_rank": "FPP段位",
            "status": "状态",
            "unban_time": "解封时间",
            "phone": "ARS",
            "note": "备注",
            "level": "等级"
        }.get(column, column)
        direction = "降序" if self.sort_reverse else "升序"
        self.status_message.set(f"已按{column_name}进行{direction}排序")
        
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))

    def update_sort_indicator(self):
        """更新排序指示器"""
        if not self.sort_column:
            return
            
        # 添加排序标记
        current_text = self.tree.heading(self.sort_column, option="text")
        if current_text.endswith(" ▲") or current_text.endswith(" ▼"):
            current_text = current_text[:-2]
            
        direction_mark = " ▼" if self.sort_reverse else " ▲"
        self.tree.heading(self.sort_column, text=current_text + direction_mark)

    def on_drag_start(self, event):
        """开始拖动行"""
        # 获取点击的区域和项目
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell" and region != "text":
            return
            
        # 获取点击的行
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # 记录拖动的项目
        self.drag_item = item
        
        # 找到该项目在原始数据中的索引
        values = self.tree.item(item, "values")
        if not values:
            return
            
        selected_name = str(values[1])
        for i, account in enumerate(self.accounts):
            if str(account["name"]) == selected_name:
                self.drag_source_index = i
                break
                
        # 设置视觉反馈 - 直接修改鼠标样式
        self.tree.config(cursor="hand2")
    
    def on_drag_motion(self, event):
        """拖动行时的处理"""
        if not self.drag_item or self.drag_source_index is None:
            return
            
        # 获取当前鼠标下方的行
        target_item = self.tree.identify_row(event.y)
        if not target_item or target_item == self.drag_item:
            return
        
        # 保持鼠标样式为拖动样式
        self.tree.config(cursor="hand2")
        
        # 尝试高亮目标行
        try:
            # 移除所有高亮
            for item in self.tree.get_children():
                self.tree.item(item, tags=())
                
            # 高亮目标行
            if target_item and target_item != self.drag_item:
                self.tree.item(target_item, tags=('highlight',))
                
            # 确保tag配置存在
            if not self.tag_exists('highlight'):
                self.tree.tag_configure('highlight', background='#ECECEC')
        except Exception as e:
            # 忽略高亮过程中的错误，保持基本拖动功能
            print(f"高亮错误: {str(e)}")
    
    def on_drag_release(self, event):
        """释放鼠标完成拖动"""
        # 恢复正常鼠标样式
        self.tree.config(cursor="")
        
        # 清除所有高亮
        try:
            for item in self.tree.get_children():
                self.tree.item(item, tags=())
        except:
            pass
        
        if not self.drag_item or self.drag_source_index is None:
            return
            
        # 获取释放时鼠标下方的行
        target_item = self.tree.identify_row(event.y)
        if not target_item or target_item == self.drag_item:
            self.drag_item = None
            self.drag_source_index = None
            return
            
        # 获取目标行的索引
        try:
            values = self.tree.item(target_item, "values")
            if not values:
                self.drag_item = None
                self.drag_source_index = None
                return
                
            target_name = str(values[1])
            target_index = None
            for i, account in enumerate(self.accounts):
                if str(account["name"]) == target_name:
                    target_index = i
                    break
                    
            if target_index is None:
                self.drag_item = None
                self.drag_source_index = None
                return
                
            # 调整账号顺序
            account = self.accounts.pop(self.drag_source_index)
            self.accounts.insert(target_index, account)
            
            # 清除任何已有的排序状态
            if self.sort_column:
                # 清除排序列上的标记
                current_text = self.tree.heading(self.sort_column, option="text")
                if current_text.endswith(" ▲") or current_text.endswith(" ▼"):
                    clean_text = current_text[:-2]
                    self.tree.heading(self.sort_column, text=clean_text)
                    
                # 重置排序状态
                old_sort_column = self.sort_column
                self.sort_column = None
                self.sort_reverse = False
                
                # 额外的状态提示
                self.status_message.set(f"手动排序模式已启用，'{old_sort_column}'列排序已取消")
                self.root.after(3000, lambda: self.status_message.set(""))
            
            # 保存自定义顺序
            self.save_custom_order()
            
            # 重新加载表格
            self.update_treeview()
            
            # 显示状态信息
            self.status_message.set(f"已调整账号 '{account['name']}' 的位置")
            self.root.after(3000, lambda: self.status_message.set(""))
        except Exception as e:
            print(f"拖动处理错误: {str(e)}")
            
        # 重置拖放状态
        self.drag_item = None
        self.drag_source_index = None
    
    def save_custom_order(self):
        """保存用户自定义的顺序"""
        # 保存每个账号的新序号
        for i, account in enumerate(self.accounts):
            account_name = str(account["name"])
            self.custom_order[account_name] = i
        
        # 保存到文件
        self.save_accounts()

    def tag_exists(self, tag_name):
        """检查tag是否已在树视图中配置"""
        try:
            # 尝试获取tag配置，如果不存在会抛出异常
            self.tree.tag_configure(tag_name)
            return True
        except Exception:
            return False

    def update_extend_button_state(self, *args):
        """更新"追3天"按钮的可用状态"""
        try:
            # 判断当前是否为封禁状态
            is_banned = self.status_var.get()
            
            # 获取当前解封时间
            unban_time_str = self.unban_time_var.get()
            
            # 默认禁用
            enable_extend = False
            
            if is_banned and unban_time_str:
                try:
                    # 计算当前封禁的时长
                    unban_time = datetime.datetime.strptime(unban_time_str, "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    hours_diff = (unban_time - now).total_seconds() / 3600
                    
                    # 只有在封禁时长接近24小时(允许1小时误差)时才启用
                    if abs(hours_diff - 24) < 1:
                        enable_extend = True
                except:
                    pass
            
            # 更新按钮状态
            if enable_extend:
                self.duration_radios["追3天"].configure(state="normal")
            else:
                self.duration_radios["追3天"].configure(state="disabled")
        except Exception as e:
            print(f"更新追3天按钮状态出错: {str(e)}")
            # 出错时禁用按钮
            try:
                self.duration_radios["追3天"].configure(state="disabled")
            except:
                pass

    # 添加网络请求功能来查询封禁状态
    def check_ban_status_online(self, player_id):
        """
        通过网络接口查询账号的封禁状态
        返回: (是否封禁, 是否查询成功, 玩家等级, account_id)
        """
        if not player_id:
            return False, False, 0, None
            
        try:
            # 调用独立的API查询函数
            return self.query_ban_api(player_id)
        except Exception as e:
            print(f"查询封禁状态出错: {str(e)}")
            return False, False, 0, None
            
    def query_ban_api(self, player_id):
        """
        独立的API查询函数，以便于未来更换API时只需修改此函数
        返回: (是否封禁, 是否查询成功, 玩家等级, account_id)
        """
        url = f"https://apiv1.pubg.plus/steam/player/banv2?player_id={player_id}"
        print(f"正在请求API: {url}")
        try:
            # 打印详细的请求信息
            print(f"开始查询玩家 {player_id} 的封禁状态...")
            
            # 添加请求头，模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)  # 增加超时时间到10秒
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # 调试用，只打印部分数据，避免数据过大
                    if "player" in data:
                        player_info = data["player"].copy()
                        if "matches" in data:
                            data_debug = data.copy()
                            data_debug["matches"] = f"[{len(data['matches'])} matches]"
                            print(f"API返回数据: {data_debug}")
                        else:
                            print(f"API返回数据: {data}")
                    else:
                        print(f"API返回数据: {data}")
                    
                    # 初始化等级为0和account_id为None
                    player_level = 0
                    account_id = None
                    
                    # 获取API返回的account_id
                    if "player" in data and "id" in data["player"]:
                        account_id = data["player"]["id"]
                        print(f"从API获取到account_id: {account_id}")
                    
                    # 如果有player信息，计算等级
                    if "player" in data and "tier" in data["player"] and "level" in data["player"]:
                        tier = data["player"]["tier"]
                        level = data["player"]["level"]
                        # 根据规则计算等级: (tier-1)*500+level
                        player_level = (tier - 1) * 500 + level
                        print(f"玩家等级信息: tier={tier}, level={level}, 计算后等级={player_level}")
                    
                    if "ban" in data and "banType" in data["ban"]:
                        # 检查封禁状态: TemporaryBan表示封禁，Innocent表示未封禁
                        ban_type = data["ban"]["banType"]
                        is_banned = ban_type == "TemporaryBan"
                        print(f"账号 {player_id} 查询结果: ban_type={ban_type}, {'已封禁' if is_banned else '未封禁'}")
                        return is_banned, True, player_level, account_id
                    else:
                        print(f"API返回数据格式错误，缺少预期字段: {data}")
                except Exception as e:
                    print(f"解析API响应JSON出错: {str(e)}")
                    print(f"原始响应内容: {response.text[:500]}...") # 只打印前500个字符
            else:
                print(f"API请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}...") # 只打印前500个字符
        except Exception as e:
            print(f"API请求异常: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印详细的异常堆栈信息
            
        return False, False, 0, None

    def update_stats_info(self):
        """更新统计信息"""
        total_accounts = len(self.accounts)
        banned_accounts = sum(1 for account in self.accounts if account["status"])
        unbanned_accounts = total_accounts - banned_accounts
        extended_bans = sum(1 for account in self.accounts if account.get("extended_ban") == "追3天")
        accounts_with_level = sum(1 for account in self.accounts if account.get("level", 0) > 0)
        
        # 更新统计信息文本
        stats_text = f"账号列表 (共{total_accounts}个账号，封禁中{banned_accounts}个，未封禁{unbanned_accounts}个，追封{extended_bans}个)"
        self.list_frame.configure(text=stats_text)
    
    def refresh_ban_status(self):
        """刷新封禁状态并更新界面"""
        # 如果后台任务正在运行，不再启动新任务
        if self.background_task_running:
            self.status_message.set("正在检查账号状态，请稍候...")
            return
            
        # 禁用刷新按钮
        self.refresh_btn.configure(state="disabled")
        
        # 显示正在刷新的提示
        self.status_message.set("正在刷新账号状态...")
        self.root.update()  # 强制更新界面以显示提示消息
        
        # 启动后台检查任务
        self.background_task_running = True
        threading.Thread(target=self.background_check_task, daemon=True).start()
        
        # 延迟启用刷新按钮，即使任务还未完成
        self.root.after(5000, lambda: self.refresh_btn.configure(state="normal"))

    def query_rank_api(self, account_id):
        """
        查询账号的段位信息
        account_id: 账号的account_id
        返回: (是否成功, tpp段位信息, fpp段位信息)
            段位信息格式为字典: {"tier": 段位名称, "subTier": 子段位, "rankPoint": 分数}
            如: {"tier": "Gold", "subTier": "4", "rankPoint": 2165}
        """
        if not account_id:
            print("账号没有account_id，无法查询段位")
            return False, None, None
            
        # 从第一个账户读取season字段，如果不存在则使用默认值35
        season_num = 35  # 默认赛季
        if self.accounts and len(self.accounts) > 0:
            # 检查第一个账户是否有season字段
            if "season" in self.accounts[0]:
                season_num = self.accounts[0]["season"]
                print(f"从accounts.json中读取赛季: {season_num}")
            else:
                # 没有找到season字段，写入默认值
                self.accounts[0]["season"] = season_num
                print(f"accounts.json中未找到season字段，写入默认值: {season_num}")
                self.save_accounts()
        
        # 构建season参数字符串
        season = f"division.bro.official.pc-2018-{season_num}"
        url = f"https://apiv1.pubg.plus/steam/player/season_r?acc_id={account_id}&season={season}"
        print(f"正在请求段位API: {url}")
        
        try:
            # 添加请求头，模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f"段位API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"段位API返回数据: {data}")
                    
                    # 初始化返回值
                    tpp_rank = None
                    fpp_rank = None
                    
                    if "attributes" in data and "rankedGameModeStats" in data["attributes"]:
                        stats = data["attributes"]["rankedGameModeStats"]
                        
                        # 获取TPP段位信息
                        if "squad" in stats:
                            squad_data = stats["squad"]
                            if "currentTier" in squad_data and "currentRankPoint" in squad_data:
                                current_tier = squad_data["currentTier"]
                                rank_point = squad_data["currentRankPoint"]
                                
                                tpp_rank = {
                                    "tier": current_tier["tier"],
                                    "subTier": current_tier["subTier"],
                                    "rankPoint": rank_point
                                }
                                print(f"获取到TPP段位: {tpp_rank}")
                        
                        # 获取FPP段位信息
                        if "squad-fpp" in stats:
                            fpp_data = stats["squad-fpp"]
                            if "currentTier" in fpp_data and "currentRankPoint" in fpp_data:
                                current_tier = fpp_data["currentTier"]
                                rank_point = fpp_data["currentRankPoint"]
                                
                                fpp_rank = {
                                    "tier": current_tier["tier"],
                                    "subTier": current_tier["subTier"],
                                    "rankPoint": rank_point
                                }
                                print(f"获取到FPP段位: {fpp_rank}")
                    
                    return True, tpp_rank, fpp_rank
                except Exception as e:
                    print(f"解析段位API响应JSON出错: {str(e)}")
                    print(f"原始响应内容: {response.text[:500]}...") # 只打印前500个字符
            else:
                print(f"段位API请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}...") # 只打印前500个字符
        except Exception as e:
            print(f"段位API请求异常: {str(e)}")
            import traceback
            traceback.print_exc()
            
        return False, None, None

    def update_account_ranks(self):
        """查询并更新所有账号的段位信息"""
        print("开始查询所有账号段位信息...")
        ranks_updated = False
        
        for idx, account in enumerate(self.accounts):
            account_name = account.get('name', '未命名')
            account_id = account.get('account_id', '')
            
            # 更新状态栏显示当前正在查询的账号
            self.root.after(0, lambda name=account_name, i=idx+1, total=len(self.accounts): 
                           self.status_message.set(f"正在查询账号段位 ({i}/{total}): {name}"))
            
            if not account_id:
                print(f"账号 {account_name} 没有account_id，跳过段位查询")
                continue
                
            print(f"正在查询账号 {account_name} 的段位信息...")
            success, tpp_rank, fpp_rank = self.query_rank_api(account_id)
            
            if success:
                # 更新TPP段位信息
                if tpp_rank:
                    # 转换段位名称
                    tier_name_map = {
                        "Bronze": "青铜",
                        "Silver": "白银",
                        "Gold": "黄金",
                        "Platinum": "铂金",
                        "Diamond": "钻石",
                        "Master": "大师"
                    }
                    
                    tier_name = tier_name_map.get(tpp_rank["tier"], tpp_rank["tier"])
                    sub_tier = tpp_rank["subTier"]
                    rank_point = tpp_rank["rankPoint"]
                    
                    # 保存rank分数到独立字段
                    account["tpp_rank_point"] = rank_point
                    
                    # 只保存基础段位格式: 黄金4
                    tpp_rank_display = f"{tier_name}{sub_tier}"
                    
                    # 检查是否需要更新
                    update_needed = False
                    if account.get("tpp_rank") != tpp_rank_display:
                        update_needed = True
                    if account.get("tpp_rank_point") != rank_point:
                        update_needed = True
                    
                    if update_needed:
                        account["tpp_rank"] = tpp_rank_display
                        print(f"账号 {account_name} TPP段位已更新: {tpp_rank_display}({rank_point})")
                        ranks_updated = True
                else:
                    # 如果没有获取到段位，直接设置为未定级
                    update_needed = False
                    if account.get("tpp_rank") != "未定级":
                        update_needed = True
                    if account.get("tpp_rank_point", 0) != 0:
                        update_needed = True
                        
                    if update_needed:
                        account["tpp_rank"] = "未定级"
                        account["tpp_rank_point"] = 0
                        print(f"账号 {account_name} TPP段位已更新为: 未定级")
                        ranks_updated = True
                
                # 更新FPP段位信息
                if fpp_rank:
                    # 转换段位名称
                    tier_name_map = {
                        "Bronze": "青铜",
                        "Silver": "白银",
                        "Gold": "黄金",
                        "Platinum": "铂金",
                        "Diamond": "钻石",
                        "Master": "大师"
                    }
                    
                    tier_name = tier_name_map.get(fpp_rank["tier"], fpp_rank["tier"])
                    sub_tier = fpp_rank["subTier"]
                    rank_point = fpp_rank["rankPoint"]
                    
                    # 保存rank分数到独立字段
                    account["fpp_rank_point"] = rank_point
                    
                    # 只保存基础段位格式: 铂金5
                    fpp_rank_display = f"{tier_name}{sub_tier}"
                    
                    # 检查是否需要更新
                    update_needed = False
                    if account.get("fpp_rank") != fpp_rank_display:
                        update_needed = True
                    if account.get("fpp_rank_point") != rank_point:
                        update_needed = True
                    
                    if update_needed:
                        account["fpp_rank"] = fpp_rank_display
                        print(f"账号 {account_name} FPP段位已更新: {fpp_rank_display}({rank_point})")
                        ranks_updated = True
                else:
                    # 如果没有获取到段位，直接设置为未定级
                    update_needed = False
                    if account.get("fpp_rank") != "未定级":
                        update_needed = True
                    if account.get("fpp_rank_point", 0) != 0:
                        update_needed = True
                    
                    if update_needed:
                        account["fpp_rank"] = "未定级"
                        account["fpp_rank_point"] = 0
                        print(f"账号 {account_name} FPP段位已更新为: 未定级")
                        ranks_updated = True
                
                # 在UI中更新显示
                self.root.after(0, lambda i=idx: self.update_single_account_ui(i))
            
            # 添加延迟以避免API请求过快
            time.sleep(1)
        
        # 如果有段位更新，保存到文件
        if ranks_updated:
            self.save_accounts()
            self.status_message.set("段位查询完成: 有段位更新")
        else:
            self.status_message.set("段位查询完成: 无段位变化")
            
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))
        
        return ranks_updated

    def refresh_rank_status(self):
        """刷新段位状态并更新界面"""
        # 如果后台任务正在运行，不再启动新任务
        if self.background_task_running:
            self.status_message.set("正在检查账号状态，请稍候...")
            return
            
        # 显示正在刷新的提示
        self.status_message.set("正在查询账号段位...")
        self.root.update()  # 强制更新界面以显示提示消息
        
        # 启动后台线程执行段位查询
        self.background_task_running = True
        
        def run_rank_query():
            try:
                # 执行段位更新
                self.update_account_ranks()
            except Exception as e:
                print(f"段位查询任务异常: {str(e)}")
                # 在主线程中更新状态
                self.root.after(0, lambda: self.status_message.set(f"段位查询出错: {str(e)}"))
            finally:
                # 重置后台任务标志
                self.background_task_running = False
        
        # 启动后台线程
        threading.Thread(target=run_rank_query, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AccountManager(root)
    root.mainloop() 
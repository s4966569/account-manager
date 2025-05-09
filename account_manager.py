import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import json
import os
import sys

class AccountManager:
    def __init__(self, root):
        self.root = root
        self.root.title("账号管理器")
        self.root.geometry("1300x600")
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
        
        # 加载账号数据
        self.load_accounts()
        
        self.create_widgets()
        self.update_treeview()
        
        # 初始不添加排序标记
        # self.update_sort_indicator()
    
    def load_accounts(self):
        """从文件加载账号数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
            except:
                self.accounts = []
        
        # 启动时检查并更新封禁状态
        self.update_ban_status()
    
    def update_ban_status(self):
        """检查并更新账号的封禁状态，返回是否有更新"""
        current_time = datetime.datetime.now()
        status_updated = False
        
        for account in self.accounts:
            if account["status"] and account["unban_time"]:
                try:
                    unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                    # 判断解封时间是否已过期
                    if current_time >= unban_time:
                        account["status"] = False  # 更新为正常状态
                        account["unban_time"] = ""  # 清空解封时间
                        status_updated = True
                except:
                    # 日期格式无效，忽略
                    pass
        
        # 如果有状态更新，保存到文件
        if status_updated:
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
        ttk.Button(self.root, text="刷新状态", command=self.refresh_ban_status, width=10).place(x=550, y=0)
        
        # 创建状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_message, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_account_list(self):
        """创建账号列表"""
        # 创建Frame - 增加宽度从600到800
        self.list_frame = ttk.LabelFrame(self.root, text="账号列表")
        self.list_frame.place(x=10, y=10, width=900, height=580)
        
        # 创建Treeview - 添加id列在ARS后面
        columns = ("number", "name", "note", "fpp_rank", "tpp_rank", "status", "unban_time", "phone", "id")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", selectmode="browse")
        
        # 配置高亮样式
        self.tree.tag_configure('highlight', background='#ECECEC')
        
        # 设置列标题，重新添加排序功能
        self.tree.heading("number", text="序号")
        self.tree.heading("name", text="账号名称")
        self.tree.heading("note", text="备注")  # 移除点击排序命令
        self.tree.heading("fpp_rank", text="FPP段位", command=lambda: self.force_sort("fpp_rank"))
        self.tree.heading("tpp_rank", text="TPP段位", command=lambda: self.force_sort("tpp_rank"))
        self.tree.heading("status", text="状态", command=lambda: self.force_sort("status"))
        self.tree.heading("unban_time", text="解封时间", command=lambda: self.force_sort("unban_time"))
        self.tree.heading("phone", text="ARS", command=lambda: self.force_sort("phone"))
        self.tree.heading("id", text="ID")
        
        # 调整列宽以适应表格总宽度
        self.tree.column("number", width=40)  # 序号列窄一些
        self.tree.column("name", width=100)
        self.tree.column("note", width=150)  # 备注列现在在第二位
        self.tree.column("fpp_rank", width=80)
        self.tree.column("tpp_rank", width=80)
        self.tree.column("status", width=60)
        self.tree.column("unban_time", width=150)
        self.tree.column("phone", width=100)
        self.tree.column("id", width=80)  # ID列宽
        
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
    
    def refresh_ban_status(self):
        """刷新封禁状态并更新界面"""
        # 调用更新封禁状态方法
        updated = self.update_ban_status()
        
        # 更新界面
        self.update_treeview()
        
        # 显示状态信息
        if updated:
            self.status_message.set("已更新账号状态，部分账号的封禁状态已改变")
        else:
            self.status_message.set("已刷新账号状态，无账号状态变化")
            
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))
    
    def create_account_form(self):
        """创建账号表单"""
        # 创建Frame - 右移表单
        form_frame = ttk.LabelFrame(self.root, text="账号详情")
        form_frame.place(x=920, y=10, width=370, height=580)
        
        # 账号名称
        ttk.Label(form_frame, text="账号名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.password_var, width=30).grid(row=1, column=1, padx=10, pady=10)
        
        # TPP段位
        ttk.Label(form_frame, text="TPP段位:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.tpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.tpp_rank_var, values=self.rank_options, width=27, state="readonly").grid(row=2, column=1, padx=10, pady=10)
        
        # FPP段位
        ttk.Label(form_frame, text="FPP段位:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.fpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.fpp_rank_var, values=self.rank_options, width=27, state="readonly").grid(row=3, column=1, padx=10, pady=10)
        
        # 手机号
        ttk.Label(form_frame, text="ARS:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.phone_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.phone_var, width=30).grid(row=4, column=1, padx=10, pady=10)
        
        # ID
        ttk.Label(form_frame, text="ID:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.id_var, width=30).grid(row=5, column=1, padx=10, pady=10)
        
        # 当前状态
        ttk.Label(form_frame, text="封禁状态:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.status_var = tk.BooleanVar()
        # 添加跟踪变量变化的回调
        self.status_var.trace_add("write", self.on_status_changed)
        
        status_frame = ttk.Frame(form_frame)
        status_frame.grid(row=6, column=1, padx=10, pady=10, sticky="w")
        ttk.Radiobutton(status_frame, text="正常 ✅", variable=self.status_var, value=False).pack(side="left")
        ttk.Radiobutton(status_frame, text="封禁 ❌", variable=self.status_var, value=True).pack(side="left", padx=10)
        
        # 解封时间
        ttk.Label(form_frame, text="解封时间:").grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.unban_time_var = tk.StringVar()
        # 添加跟踪变量变化的回调，用于检测手动修改
        self.unban_time_var.trace_add("write", self.on_unban_time_changed)
        ttk.Entry(form_frame, textvariable=self.unban_time_var, width=30).grid(row=7, column=1, padx=10, pady=10)
        
        # 标记封禁 - 改为RadioButton横向排列
        ttk.Label(form_frame, text="封禁时长:").grid(row=8, column=0, padx=10, pady=10, sticky="w")
        ban_frame = ttk.Frame(form_frame)
        ban_frame.grid(row=8, column=1, padx=10, pady=10, sticky="w")
        
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
        ttk.Label(form_frame, text="备注:").grid(row=9, column=0, padx=10, pady=10, sticky="nw")
        self.note_text = tk.Text(form_frame, width=30, height=3)
        self.note_text.grid(row=9, column=1, padx=10, pady=10, sticky="w")
        
        # 按钮区域
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=20)
        
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
        self.password_var.set("")
        self.tpp_rank_var.set("")
        self.fpp_rank_var.set("")
        self.phone_var.set("")
        self.id_var.set("")  # 清空ID
        self.status_var.set(False)
        self.unban_time_var.set("")
        self.ban_duration_var.set("无")  # 默认为"无"
        
        # 清空备注文本框
        self.note_text.delete("1.0", tk.END)
        
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
        
        # 更新"追3天"按钮状态
        self.update_extend_button_state()
    
    def on_duration_changed(self, *args):
        """当封禁时长变化时触发"""
        duration = self.ban_duration_var.get()
        
        if duration == "无":
            # 选择"无"时，状态设为正常
            self.status_var.set(False)
            # 清空解封时间
            self.unban_time_var.set("")
        elif duration == "追3天":
            # 选择"追3天"时，处理追加封禁
            self.status_var.set(True)  # 确保设为封禁状态
            
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
                        # 计算还需要追加的小时数，使总时长达到3天
                        hours_in_three_days = 72  # 3天=72小时
                        if hours_from_now < hours_in_three_days:
                            # 未满3天，追加时间
                            additional_hours = hours_in_three_days - hours_from_now
                            new_unban_time = current_unban_time + datetime.timedelta(hours=additional_hours)
                        else:
                            # 已经超过3天，不变
                            new_unban_time = current_unban_time
                            
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
        
        account = {
            "name": name,
            "password": self.password_var.get(),
            "tpp_rank": self.tpp_rank_var.get(),
            "fpp_rank": self.fpp_rank_var.get(),
            "phone": self.phone_var.get(),
            "id": self.id_var.get(),  # 保存ID
            "status": self.status_var.get(),
            "unban_time": self.unban_time_var.get(),
            "note": note_text  # 使用Text控件的内容
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
        
        # 更新统计信息
        stats_text = f"账号列表 (共{total_accounts}个账号，封禁中{banned_accounts}个，未封禁{unbanned_accounts}个)"
        self.list_frame.configure(text=stats_text)
        
        # 排序账号数据
        sorted_accounts = self.accounts.copy()
        
        # 检查是否所有账号都是未封禁状态
        all_unbanned = all(not account["status"] for account in sorted_accounts)
        
        if self.sort_column:
            # 如果有排序列，则根据排序列排序
            if self.sort_column == "tpp_rank" or self.sort_column == "fpp_rank":
                # 按段位排序（使用预设的段位序列）
                sorted_accounts.sort(
                    key=lambda x: self.rank_map.get(x[self.sort_column], 0),
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
        # 默认不进行排序，保持账号添加的顺序
        # 移除默认按TPP段位排序的代码
        # elif all_unbanned:
        #     sorted_accounts.sort(
        #         key=lambda x: self.rank_map.get(x["tpp_rank"], 0),
        #         reverse=False  # 默认从低到高
        #     )
        
        # 添加账号数据，包括ID列
        for i, account in enumerate(sorted_accounts):
            status = "❌" if account["status"] else "✅"
            # 确保账号对象有备注字段和ID字段
            note = account.get("note", "")
            account_id = account.get("id", "")
            
            # 格式化解封时间为简略格式
            unban_time_display = ""
            if account["status"] and account["unban_time"]:
                try:
                    unban_time = datetime.datetime.strptime(account["unban_time"], "%Y-%m-%d %H:%M:%S")
                    unban_time_display = unban_time.strftime("%m-%d %H:%M")
                except:
                    unban_time_display = account["unban_time"]
            
            # 插入数据的顺序需要与列顺序一致
            self.tree.insert("", "end", values=(
                i + 1,  # 序号从1开始
                str(account["name"]),
                str(note),
                str(account["fpp_rank"]),
                str(account["tpp_rank"]),
                status,
                unban_time_display,
                str(account["phone"]),
                str(account_id)
            ))
    
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
                self.password_var.set(account["password"])
                self.tpp_rank_var.set(account["tpp_rank"])
                self.fpp_rank_var.set(account["fpp_rank"])
                self.phone_var.set(account["phone"])
                self.id_var.set(account.get("id", ""))  # 设置ID
                self.status_var.set(account["status"])
                self.unban_time_var.set(account["unban_time"])
                
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
            "note": "备注"
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

if __name__ == "__main__":
    root = tk.Tk()
    app = AccountManager(root)
    root.mainloop() 
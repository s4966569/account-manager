import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import json
import os

class AccountManager:
    def __init__(self, root):
        self.root = root
        self.root.title("账号管理器")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)
        
        # 数据文件路径
        self.data_file = "accounts.json"
        
        # 账号数据
        self.accounts = []
        self.load_accounts()
        
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
        self.ban_duration_options = ["无", "24小时", "72小时", "7天", "15天", "30天", "自定义"]
        
        # 用于记住上次选择的非"无"封禁时长
        self.last_duration = "24小时"
        
        # 创建状态栏
        self.status_var = tk.StringVar()
        self.status_message = tk.StringVar()
        
        # 排序相关变量
        self.sort_column = ""  # 当前排序的列
        self.sort_reverse = False  # 是否逆序
        
        # 统计信息变量
        self.stats_var = tk.StringVar(value="账号列表")
        
        self.create_widgets()
        self.update_treeview()
    
    def load_accounts(self):
        """从文件加载账号数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
            except:
                self.accounts = []
    
    def save_accounts(self):
        """保存账号数据到文件"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)
    
    def create_widgets(self):
        """创建界面元素"""
        # 创建左侧表格
        self.create_account_list()
        
        # 创建右侧表单
        self.create_account_form()
        
        # 创建状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_message, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_account_list(self):
        """创建账号列表"""
        # 创建Frame
        self.list_frame = ttk.LabelFrame(self.root, text="账号列表")
        self.list_frame.place(x=10, y=10, width=600, height=580)
        
        # 创建Treeview - 手机号列放到最后面，交换TPP和FPP位置
        columns = ("name", "fpp_rank", "tpp_rank", "status", "unban_time", "phone")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", selectmode="browse")
        
        # 设置列标题 - 删除旧的排序命令
        self.tree.heading("name", text="账号名称")
        self.tree.heading("fpp_rank", text="FPP段位")
        self.tree.heading("tpp_rank", text="TPP段位")
        self.tree.heading("status", text="状态")
        self.tree.heading("unban_time", text="解封时间")
        self.tree.heading("phone", text="手机号")
        
        # 设置列宽
        self.tree.column("name", width=100)
        self.tree.column("fpp_rank", width=80)
        self.tree.column("tpp_rank", width=80)
        self.tree.column("status", width=50)
        self.tree.column("unban_time", width=150)
        self.tree.column("phone", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_account_selected)
        
        # 绑定双击事件以复制账号名称
        self.tree.bind("<Double-1>", self.copy_account_name)
    
    def create_account_form(self):
        """创建账号表单"""
        # 创建Frame
        form_frame = ttk.LabelFrame(self.root, text="账号详情")
        form_frame.place(x=620, y=10, width=370, height=580)
        
        # 账号名称
        ttk.Label(form_frame, text="账号名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        # 密码
        ttk.Label(form_frame, text="密码:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.password_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.password_var, width=30, show="*").grid(row=1, column=1, padx=10, pady=10)
        
        # TPP段位
        ttk.Label(form_frame, text="TPP段位:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.tpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.tpp_rank_var, values=self.rank_options, width=27).grid(row=2, column=1, padx=10, pady=10)
        
        # FPP段位
        ttk.Label(form_frame, text="FPP段位:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.fpp_rank_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.fpp_rank_var, values=self.rank_options, width=27).grid(row=3, column=1, padx=10, pady=10)
        
        # 手机号
        ttk.Label(form_frame, text="手机号:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.phone_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.phone_var, width=30).grid(row=4, column=1, padx=10, pady=10)
        
        # 当前状态
        ttk.Label(form_frame, text="封禁状态:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.status_var = tk.BooleanVar()
        # 添加跟踪变量变化的回调
        self.status_var.trace_add("write", self.on_status_changed)
        
        status_frame = ttk.Frame(form_frame)
        status_frame.grid(row=5, column=1, padx=10, pady=10, sticky="w")
        ttk.Radiobutton(status_frame, text="正常 ✅", variable=self.status_var, value=False).pack(side="left")
        ttk.Radiobutton(status_frame, text="封禁 ❌", variable=self.status_var, value=True).pack(side="left", padx=10)
        
        # 解封时间
        ttk.Label(form_frame, text="解封时间:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.unban_time_var = tk.StringVar()
        # 添加跟踪变量变化的回调，用于检测手动修改
        self.unban_time_var.trace_add("write", self.on_unban_time_changed)
        ttk.Entry(form_frame, textvariable=self.unban_time_var, width=30).grid(row=6, column=1, padx=10, pady=10)
        
        # 标记封禁 - 改为RadioButton横向排列
        ttk.Label(form_frame, text="封禁时长:").grid(row=7, column=0, padx=10, pady=10, sticky="w")
        ban_frame = ttk.Frame(form_frame)
        ban_frame.grid(row=7, column=1, padx=10, pady=10, sticky="w")
        
        # 创建两行RadioButton，每行4个
        ban_row1 = ttk.Frame(ban_frame)
        ban_row1.pack(fill="x", pady=2)
        ban_row2 = ttk.Frame(ban_frame)
        ban_row2.pack(fill="x", pady=2)
        
        self.ban_duration_var = tk.StringVar(value="无")  # 默认选中"无"选项
        # 添加跟踪变量变化的回调
        self.ban_duration_var.trace_add("write", self.on_duration_changed)
        
        # 第一行放4个选项
        for i, duration in enumerate(self.ban_duration_options[:4]):
            ttk.Radiobutton(ban_row1, text=duration, variable=self.ban_duration_var, value=duration).pack(side="left", padx=5)
        
        # 第二行放3个选项
        for duration in self.ban_duration_options[4:]:
            ttk.Radiobutton(ban_row2, text=duration, variable=self.ban_duration_var, value=duration).pack(side="left", padx=5)
        
        # 按钮区域
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="新建", command=self.clear_form).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="保存", command=self.save_account).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="删除", command=self.delete_account).pack(side="left", padx=10)
    
    def clear_form(self):
        """清空表单"""
        self.current_account_id = None
        self.name_var.set("")
        self.password_var.set("")
        self.tpp_rank_var.set("")
        self.fpp_rank_var.set("")
        self.phone_var.set("")
        self.status_var.set(False)
        self.unban_time_var.set("")
        self.ban_duration_var.set("无")  # 默认为"无"
        
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
    
    def on_duration_changed(self, *args):
        """当封禁时长变化时触发"""
        duration = self.ban_duration_var.get()
        
        if duration == "无":
            # 选择"无"时，状态设为正常
            self.status_var.set(False)
            # 清空解封时间
            self.unban_time_var.set("")
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
    
    def save_account(self):
        """保存账号信息"""
        name = self.name_var.get().strip()
        
        if not name:
            messagebox.showwarning("警告", "账号名称不能为空")
            return
        
        # 确保如果是封禁状态，强制计算一次解封时间
        if self.status_var.get():
            self.calculate_unban_time()
        
        account = {
            "name": name,
            "password": self.password_var.get(),
            "tpp_rank": self.tpp_rank_var.get(),
            "fpp_rank": self.fpp_rank_var.get(),
            "phone": self.phone_var.get(),
            "status": self.status_var.get(),
            "unban_time": self.unban_time_var.get()
        }
        
        if hasattr(self, 'current_account_id') and self.current_account_id is not None:
            # 更新现有账号
            self.accounts[self.current_account_id] = account
        else:
            # 添加新账号
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
        
        if messagebox.askyesno("确认", "确定要删除该账号吗？"):
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
        # 默认排序：如果没有指定排序列且所有账号都是未封禁状态，则按TPP段位排序
        elif all_unbanned:
            sorted_accounts.sort(
                key=lambda x: self.rank_map.get(x["tpp_rank"], 0),
                reverse=False  # 默认从低到高
            )
        
        # 添加账号数据，交换TPP和FPP位置
        for account in sorted_accounts:
            status = "❌" if account["status"] else "✅"
            self.tree.insert("", "end", values=(
                account["name"],
                account["fpp_rank"],
                account["tpp_rank"],
                status,
                account["unban_time"],
                account["phone"]
            ))
    
    def on_account_selected(self, event):
        """选中账号时的处理"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        selected_name = item["values"][0]
        
        # 查找对应的账号
        for i, account in enumerate(self.accounts):
            if account["name"] == selected_name:
                self.current_account_id = i
                self.name_var.set(account["name"])
                self.password_var.set(account["password"])
                self.tpp_rank_var.set(account["tpp_rank"])
                self.fpp_rank_var.set(account["fpp_rank"])
                self.phone_var.set(account["phone"])
                self.status_var.set(account["status"])
                self.unban_time_var.set(account["unban_time"])
                
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
    
    def copy_account_name(self, event):
        """复制账号名称到剪贴板"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        account_name = item["values"][0]
        
        # 将账号名称复制到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(account_name)
        
        # 在状态栏显示提示
        self.status_message.set(f"已复制账号：{account_name}")
        
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))
    
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
            "unban_time": "解封时间"
        }.get(column, column)
        self.status_message.set(f"已按{column_name}进行{direction}排序")
        
        # 3秒后清空状态栏
        self.root.after(3000, lambda: self.status_message.set(""))

if __name__ == "__main__":
    root = tk.Tk()
    app = AccountManager(root)
    root.mainloop() 
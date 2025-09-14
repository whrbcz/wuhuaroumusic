import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
import pygame
import threading
import time
import os
import tempfile
import subprocess
import platform
import re
import json
import random
import hashlib
import smtplib
from email.mime.text import MIMEText

# 初始化pygame音频系统
pygame.mixer.init()

# 邮箱配置 (需要用户自行配置)
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",  # 例如: smtp.qq.com, smtp.gmail.com
    "smtp_port": 587,
    "smtp_username": "wzss_0801@qq.com",
    "smtp_password": "ifrjmzuziewobeed",  # QQ邮箱使用授权码
    "sender": "wzss_0801@qq.com"
}

# 本地存储配置
LOCAL_STORAGE_CONFIG = {
    "data_dir": os.path.join(os.path.expanduser("~"), ".netease_music_player"),
    "users_file": "users.json"
}

class UserAuth:
    """用户认证管理类 - 使用本地存储"""
    def __init__(self):
        self.logged_in = False
        self.current_user = None
        self.users = self.load_users()
        
        # 确保数据目录存在
        if not os.path.exists(LOCAL_STORAGE_CONFIG["data_dir"]):
            os.makedirs(LOCAL_STORAGE_CONFIG["data_dir"])
    
    def get_users_file_path(self):
        """获取用户数据文件路径"""
        return os.path.join(
            LOCAL_STORAGE_CONFIG["data_dir"],
            LOCAL_STORAGE_CONFIG["users_file"]
        )
    
    def load_users(self):
        """从本地文件加载用户数据"""
        try:
            file_path = self.get_users_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            # 如果文件不存在，返回空字典
            return {}
        except Exception as e:
            print(f"加载用户数据失败: {e}")
            return {}
    
    def save_users(self):
        """保存用户数据到本地文件"""
        try:
            file_path = self.get_users_file_path()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存用户数据失败: {e}")
            return False
    
    def generate_verification_code(self):
        """生成6位数字验证码"""
        return str(random.randint(100000, 999999))
    
    def send_verification_email(self, email):
        """发送验证码到邮箱"""
        try:
            code = self.generate_verification_code()
            subject = "五花肉云音乐 - 邮箱验证"
            content = f"您的验证码是: {code}，有效期5分钟。"
            
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = EMAIL_CONFIG["sender"]
            msg['To'] = email
            
            server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
            server.starttls()
            server.login(EMAIL_CONFIG["smtp_username"], EMAIL_CONFIG["smtp_password"])
            server.sendmail(EMAIL_CONFIG["sender"], [email], msg.as_string())
            server.quit()
            
            return code
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return None
    
    def register(self, username, email, password, code, verification_code):
        """用户注册"""
        if code != verification_code:
            return False, "验证码不正确"
            
        if username in self.users:
            return False, "用户名已存在"
            
        if any(user["email"] == email for user in self.users.values()):
            return False, "邮箱已被注册"
            
        # 密码加密存储
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        self.users[username] = {
            "email": email,
            "password": hashed_password,
            "register_time": time.time()  # 移除is_vip字段
        }
        
        if self.save_users():
            return True, "注册成功"
        else:
            return False, "注册失败，请稍后重试"
    
    def login(self, username, password):
        """用户登录"""
        if username not in self.users:
            return False, "用户名不存在"
            
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if self.users[username]["password"] != hashed_password:
            return False, "密码不正确"
            
        self.logged_in = True
        self.current_user = username
        return True, "登录成功"
    
    def logout(self):
        """用户登出"""
        self.logged_in = False
        self.current_user = None

class AuthDialog:
    """登录注册对话框"""
    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("用户登录/注册")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.verification_code = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # 创建标签页
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 登录标签页
        login_frame = ttk.Frame(notebook)
        notebook.add(login_frame, text="登录")
        
        # 用户名
        ttk.Label(login_frame, text="用户名:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.login_username = ttk.Entry(login_frame)
        self.login_username.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 密码
        ttk.Label(login_frame, text="密码:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.login_password = ttk.Entry(login_frame, show="*")
        self.login_password.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 登录按钮
        login_btn = ttk.Button(login_frame, text="登录", command=self.do_login)
        login_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 注册标签页
        register_frame = ttk.Frame(notebook)
        notebook.add(register_frame, text="注册")
        
        # 用户名
        ttk.Label(register_frame, text="用户名:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.reg_username = ttk.Entry(register_frame)
        self.reg_username.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 邮箱
        ttk.Label(register_frame, text="邮箱:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.reg_email = ttk.Entry(register_frame)
        self.reg_email.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 密码
        ttk.Label(register_frame, text="密码:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.reg_password = ttk.Entry(register_frame, show="*")
        self.reg_password.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 验证码
        code_frame = ttk.Frame(register_frame)
        code_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(code_frame, text="验证码:").pack(side=tk.LEFT, padx=5)
        self.reg_code = ttk.Entry(code_frame, width=10)
        self.reg_code.pack(side=tk.LEFT, padx=5)
        
        self.send_code_btn = ttk.Button(code_frame, text="发送验证码", command=self.send_verification)
        self.send_code_btn.pack(side=tk.LEFT, padx=5)
        
        # 注册按钮
        reg_btn = ttk.Button(register_frame, text="注册", command=self.do_register)
        reg_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        # 配置列权重，使输入框可以拉伸
        for frame in [login_frame, register_frame]:
            frame.columnconfigure(1, weight=1)
    
    def send_verification(self):
        email = self.reg_email.get().strip()
        if not email:
            messagebox.showwarning("提示", "请输入邮箱")
            return
            
        self.verification_code = self.auth_manager.send_verification_email(email)
        if self.verification_code:
            messagebox.showinfo("提示", "验证码已发送到您的邮箱")
        else:
            messagebox.showerror("错误", "发送验证码失败，请检查邮箱配置")
    
    def do_register(self):
        username = self.reg_username.get().strip()
        email = self.reg_email.get().strip()
        password = self.reg_password.get().strip()
        code = self.reg_code.get().strip()
        
        if not all([username, email, password, code]):
            messagebox.showwarning("提示", "请填写所有字段")
            return
            
        if not self.verification_code:
            messagebox.showwarning("提示", "请先获取验证码")
            return
            
        success, msg = self.auth_manager.register(username, email, password, code, self.verification_code)
        if success:
            messagebox.showinfo("成功", msg)
            self.dialog.destroy()
        else:
            messagebox.showerror("错误", msg)
    
    def do_login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()
        
        if not all([username, password]):
            messagebox.showwarning("提示", "请填写用户名和密码")
            return
            
        success, msg = self.auth_manager.login(username, password)
        if success:
            messagebox.showinfo("成功", msg)
            self.dialog.destroy()
        else:
            messagebox.showerror("错误", msg)

class NeteaseMusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("五花肉云音乐 正式版")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 初始化用户认证 - 使用本地存储
        self.auth_manager = UserAuth()
        
        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))
        self.style.configure("Treeview", font=("SimHei", 10))
        
        # 当前播放状态
        self.playing = False
        self.paused = False
        self.current_song = None
        self.song_url = None
        self.playlist = []
        self.current_index = -1
        self.total_length = 0  # 歌曲总时长（秒）
        self.temp_file = None  # 临时文件路径
        self.use_alternative_player = False  # 是否使用替代播放器
        self.lyrics = []  # 歌词列表，格式: [(时间(秒), 歌词), ...]
        self.current_lyric_index = -1  # 当前歌词索引
        self.comments = []  # 评论列表
        self.comment_offset = 0  # 评论偏移量，用于分页加载
        self.comment_limit = 20  # 每次加载的评论数量
        
        # 创建UI
        self.create_widgets()
        
        # API相关
        self.api_url = "https://music.163.com/api"
        self.search_api = "https://music.163.com/api/search/get"
        self.lyric_api = "https://music.163.com/api/song/lyric"
        self.comment_api = "https://music.163.com/api/v1/resource/comments/R_SO_4_"
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部搜索框、按钮和用户状态
        top_frame = ttk.Frame(main_frame, padding="5")
        top_frame.pack(fill=tk.X)
        
        # 用户状态和操作按钮
        user_frame = ttk.Frame(top_frame)
        user_frame.pack(side=tk.LEFT, padx=5)
        
        self.user_status_var = tk.StringVar()
        
        # 定义登录和退出按钮
        self.login_btn = ttk.Button(user_frame, text="登录/注册", command=self.show_auth_dialog)
        self.login_btn.pack(side=tk.LEFT, padx=5)
        
        self.logout_btn = ttk.Button(user_frame, text="退出登录", command=self.logout, state=tk.DISABLED)
        self.logout_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(user_frame, textvariable=self.user_status_var).pack(side=tk.LEFT, padx=5)
        
        # 搜索框和按钮
        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<Return>", lambda event: self.search_music())
        
        search_btn = ttk.Button(search_frame, text="搜索", command=self.search_music)
        search_btn.pack(side=tk.RIGHT, padx=5)
        
        # 中间内容区域（左侧歌曲列表，右侧歌词和评论）
        content_frame = ttk.Frame(main_frame, padding="5")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧歌曲列表
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 搜索结果列表
        columns_widths = [50, 200, 150, 180, 80]
        columns = ("序号", "歌曲名", "歌手", "专辑", "时长")
        
        # 搜索结果树状视图
        self.song_tree = ttk.Treeview(left_frame, columns=columns, show="headings")
        for i, col in enumerate(columns):
            self.song_tree.heading(col, text=col)
            self.song_tree.column(col, width=columns_widths[i], anchor=tk.CENTER if i in [0, 4] else tk.W)
        
        self.song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 搜索结果滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.song_tree.configure(yscrollcommand=scrollbar.set)
        
        # 双击播放歌曲
        self.song_tree.bind("<Double-1>", self.play_selected_song)
        
        # 右侧歌词和评论区域
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 歌词和评论标签页
        self.right_notebook = ttk.Notebook(right_frame)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 歌词显示区域
        lyric_tab = ttk.LabelFrame(self.right_notebook, text="歌词", padding="5")
        self.right_notebook.add(lyric_tab, text="歌词")
        
        # 歌词显示文本框
        self.lyric_text = tk.Text(lyric_tab, wrap=tk.WORD, font=("SimHei", 12), 
                                 bg="#f0f0f0", relief=tk.FLAT)
        self.lyric_text.pack(fill=tk.BOTH, expand=True)
        self.lyric_text.config(state=tk.DISABLED)  # 设置为只读
        
        # 歌词滚动条
        lyric_scrollbar = ttk.Scrollbar(lyric_tab, orient=tk.VERTICAL, 
                                       command=self.lyric_text.yview)
        lyric_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lyric_text.configure(yscrollcommand=lyric_scrollbar.set)
        
        # 评论显示区域
        comment_tab = ttk.LabelFrame(self.right_notebook, text="评论", padding="5")
        self.right_notebook.add(comment_tab, text="评论")
        
        # 评论显示文本框
        self.comment_text = scrolledtext.ScrolledText(comment_tab, wrap=tk.WORD, 
                                                     font=("SimHei", 10), bg="#f0f0f0")
        self.comment_text.pack(fill=tk.BOTH, expand=True)
        self.comment_text.config(state=tk.DISABLED)  # 设置为只读
        
        # 评论按钮区域
        comment_buttons = ttk.Frame(comment_tab)
        comment_buttons.pack(pady=5, fill=tk.X)
        
        # 评论加载按钮
        self.load_comment_btn = ttk.Button(comment_buttons, text="加载评论", 
                                          command=self.load_comments)
        self.load_comment_btn.pack(side=tk.LEFT, padx=5)
        self.load_comment_btn.config(state=tk.DISABLED)  # 初始禁用
        
        # 加载更多评论按钮
        self.load_more_btn = ttk.Button(comment_buttons, text="加载更多", 
                                       command=self.load_more_comments)
        self.load_more_btn.pack(side=tk.LEFT, padx=5)
        self.load_more_btn.config(state=tk.DISABLED)  # 初始禁用
        
        # 评论计数显示
        self.comment_count_var = tk.StringVar()
        self.comment_count_var.set("评论数量: 0")
        ttk.Label(comment_buttons, textvariable=self.comment_count_var).pack(side=tk.RIGHT, padx=5)
        
        # 当前播放信息
        self.now_playing_var = tk.StringVar()
        self.now_playing_var.set("未播放任何歌曲")
        now_playing_label = ttk.Label(main_frame, textvariable=self.now_playing_var, 
                                     font=("SimHei", 12, "bold"))
        now_playing_label.pack(fill=tk.X, pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(main_frame, variable=self.progress_var, 
                                     from_=0, to=100, command=self.set_progress)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 时间显示
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X)
        
        self.current_time_var = tk.StringVar()
        self.current_time_var.set("00:00")
        current_time_label = ttk.Label(time_frame, textvariable=self.current_time_var)
        current_time_label.pack(side=tk.LEFT)
        
        self.total_time_var = tk.StringVar()
        self.total_time_var.set("00:00")
        total_time_label = ttk.Label(time_frame, textvariable=self.total_time_var)
        total_time_label.pack(side=tk.RIGHT)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame, padding="10")
        control_frame.pack(fill=tk.X)
        
        prev_btn = ttk.Button(control_frame, text="上一首", command=self.play_previous)
        prev_btn.pack(side=tk.LEFT, padx=10)
        
        self.play_btn = ttk.Button(control_frame, text="播放", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=10)
        
        next_btn = ttk.Button(control_frame, text="下一首", command=self.play_next)
        next_btn.pack(side=tk.LEFT, padx=10)
        
        # 添加播放模式切换按钮
        self.player_mode_var = tk.StringVar(value="默认播放器")
        self.mode_btn = ttk.Button(control_frame, textvariable=self.player_mode_var, 
                                 command=self.toggle_player_mode)
        self.mode_btn.pack(side=tk.LEFT, padx=10)
        
        volume_btn = ttk.Button(control_frame, text="音量", command=self.show_volume_dialog)
        volume_btn.pack(side=tk.RIGHT, padx=10)
        
        download_btn = ttk.Button(control_frame, text="下载", command=self.download_selected)
        download_btn.pack(side=tk.RIGHT, padx=10)
        
        # 音量控制
        self.volume_var = tk.DoubleVar()
        self.volume_var.set(pygame.mixer.music.get_volume() * 100)
        volume_scale = ttk.Scale(control_frame, variable=self.volume_var, 
                                from_=0, to=100, command=self.set_volume)
        volume_scale.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
        
        # 添加状态栏显示网络状态
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化用户状态
        self.update_user_status()
    
    def update_user_status(self):
        """更新用户状态显示"""
        if self.auth_manager.logged_in:
            # 移除VIP用户类型显示
            self.user_status_var.set(f"当前用户: {self.auth_manager.current_user}")
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
        else:
            self.user_status_var.set("未登录")
            self.login_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)
    
    def show_auth_dialog(self):
        """显示登录注册对话框"""
        dialog = AuthDialog(self.root, self.auth_manager)
        self.root.wait_window(dialog.dialog)
        self.update_user_status()
    
    def logout(self):
        """用户退出登录"""
        self.auth_manager.logout()
        self.update_user_status()
        messagebox.showinfo("提示", "已成功退出登录")
        
        # 移除VIP歌曲相关的停止播放逻辑

    def toggle_player_mode(self):
        """切换播放器模式"""
        self.use_alternative_player = not self.use_alternative_player
        if self.use_alternative_player:
            self.player_mode_var.set("系统播放器")
            messagebox.showinfo("提示", "已切换到系统播放器模式，兼容性更好但进度条和歌词可能不准确")
        else:
            self.player_mode_var.set("默认播放器")
            messagebox.showinfo("提示", "已切换到默认播放器模式")
        
        # 切换模式时停止当前播放
        if self.playing:
            self.stop_playback()
    
    def search_music(self):
        """搜索音乐，显示所有歌曲（移除VIP标注）"""
        keyword = self.search_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        
        # 清空现有列表
        for item in self.song_tree.get_children():
            self.song_tree.delete(item)
        
        try:
            self.status_var.set("正在搜索...")
            # 发送搜索请求
            params = {
                "s": keyword,
                "type": 1,  # 1表示歌曲
                "offset": 0,
                "limit": 30
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Referer": "https://music.163.com/"
            }
            
            response = requests.get(self.search_api, params=params, headers=headers)
            data = response.json()
            
            if data.get("code") == 200 and data.get("result"):
                # 获取所有搜索结果
                self.playlist = data["result"].get("songs", [])
                
                self.status_var.set(f"找到 {len(self.playlist)} 首歌曲")
                
                # 显示搜索结果（移除VIP标记）
                for i, song in enumerate(self.playlist, 1):
                    song_name = song["name"]
                    artists = "/".join([artist["name"] for artist in song["artists"]])
                    album = song["album"]["name"]
                    duration = self.format_time(song["duration"] // 1000)  # 转换为秒
                    self.song_tree.insert("", tk.END, values=(i, song_name, artists, album, duration))
            else:
                messagebox.showerror("错误", "搜索失败，请重试")
                self.status_var.set("搜索失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"搜索时发生错误: {str(e)}")
            self.status_var.set("搜索错误")
    
    def format_time(self, seconds):
        """将秒数格式化为 MM:SS 格式"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_song_url(self, song_id):
        """获取歌曲播放URL"""
        try:
            # 使用第三方API获取播放链接
            url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
            return url
        except Exception as e:
            print(f"获取歌曲URL失败: {str(e)}")
            return None
    
    def get_lyrics(self, song_id):
        """获取歌曲歌词"""
        try:
            params = {
                "id": song_id,
                "lv": -1,
                "kv": -1,
                "tv": -1
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Referer": "https://music.163.com/"
            }
            
            response = requests.get(self.lyric_api, params=params, headers=headers)
            data = response.json()
            
            if data.get("code") == 200:
                # 优先使用带时间戳的歌词
                lyric_text = data.get("lrc", {}).get("lyric", "")
                if not lyric_text:
                    # 没有带时间戳的歌词，使用普通歌词
                    lyric_text = data.get("tlyric", {}).get("lyric", "")
                
                return self.parse_lyrics(lyric_text)
            return []
        except Exception as e:
            print(f"获取歌词失败: {str(e)}")
            return []
    
    def parse_lyrics(self, lyric_text):
        """解析歌词文本为时间-歌词对列表"""
        lyrics = []
        # 匹配歌词时间格式 [mm:ss.ms]
        pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
        
        for line in lyric_text.split('\n'):
            match = pattern.match(line)
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                lyric = match.group(3).strip()
                if lyric:  # 只添加非空歌词
                    total_seconds = minutes * 60 + seconds
                    lyrics.append((total_seconds, lyric))
        
        # 按时间排序
        lyrics.sort()
        return lyrics
    
    def display_lyrics(self):
        """显示歌词到文本框"""
        self.lyric_text.config(state=tk.NORMAL)
        self.lyric_text.delete(1.0, tk.END)
        
        if not self.lyrics:
            self.lyric_text.insert(tk.END, "暂无歌词")
            self.lyric_text.config(state=tk.DISABLED)
            return
        
        # 添加所有歌词
        for time_stamp, lyric in self.lyrics:
            self.lyric_text.insert(tk.END, f"{lyric}\n")
        
        self.lyric_text.config(state=tk.DISABLED)
        self.current_lyric_index = -1  # 重置当前歌词索引
    
    def update_lyric_display(self, current_time):
        """根据当前播放时间更新歌词显示，高亮当前歌词"""
        if not self.lyrics or self.current_lyric_index >= len(self.lyrics) - 1:
            return
        
        # 找到当前应该显示的歌词
        new_index = self.current_lyric_index
        for i in range(len(self.lyrics)):
            if self.lyrics[i][0] > current_time:
                new_index = i - 1
                break
        else:
            new_index = len(self.lyrics) - 1
        
        # 如果歌词索引有变化，更新高亮
        if new_index != self.current_lyric_index and new_index >= 0:
            self.current_lyric_index = new_index
            
            # 取消之前的高亮
            self.lyric_text.tag_remove("highlight", 1.0, tk.END)
            
            # 高亮当前歌词
            line_num = new_index + 1
            self.lyric_text.tag_add("highlight", f"{line_num}.0", f"{line_num}.end")
            self.lyric_text.tag_config("highlight", background="#ffffcc", font=("SimHei", 12, "bold"))
            
            # 滚动到当前歌词
            self.lyric_text.see(f"{line_num}.0")
    
    def get_comments(self, song_id, offset=0, limit=20):
        """获取歌曲评论，支持分页"""
        try:
            url = f"{self.comment_api}{song_id}"
            params = {
                "limit": limit,
                "offset": offset,
                "csrf_token": ""
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Referer": "https://music.163.com/"
            }
            
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            
            if data.get("code") == 200:
                total_comments = data.get("total", 0)  # 获取评论总数
                return data.get("comments", []), total_comments
            return [], 0
        except Exception as e:
            print(f"获取评论失败: {str(e)}")
            return [], 0
    
    def display_comments(self, append=False):
        """显示评论到文本框，支持追加模式"""
        self.comment_text.config(state=tk.NORMAL)
        
        # 如果不是追加模式，则清空现有内容
        if not append:
            self.comment_text.delete(1.0, tk.END)
        
        if not self.comments:
            self.comment_text.insert(tk.END, "暂无评论")
            self.comment_text.config(state=tk.DISABLED)
            return
        
        # 添加评论（从偏移位置开始）
        start_index = len(self.comments) - len(self.new_comments) if append else 0
        for i in range(start_index, len(self.comments)):
            comment = self.comments[i]
            user = comment.get("user", {}).get("nickname", "未知用户")
            content = comment.get("content", "")
            time_str = time.strftime("%Y-%m-%d %H:%M", 
                                    time.localtime(comment.get("time", 0)/1000))
            likes = comment.get("likedCount", 0)
            
            self.comment_text.insert(tk.END, f"{i+1}. {user} ({time_str})\n")
            self.comment_text.insert(tk.END, f"   {content}\n")
            self.comment_text.insert(tk.END, f"   点赞: {likes}\n\n")
        
        # 更新评论计数显示
        self.comment_count_var.set(f"评论数量: {len(self.comments)}/{self.total_comment_count}")
        
        self.comment_text.config(state=tk.DISABLED)
        
        # 如果是追加评论，滚动到底部
        if append:
            self.comment_text.see(tk.END)
    
    def load_comments(self):
        """加载并显示当前歌曲的评论（重新开始加载）"""
        if not self.current_song:
            messagebox.showwarning("提示", "请先播放一首歌曲")
            return
        
        # 重置评论状态
        self.comments = []
        self.comment_offset = 0
        
        self.status_var.set("正在加载评论...")
        self.comment_text.config(state=tk.NORMAL)
        self.comment_text.delete(1.0, tk.END)
        self.comment_text.insert(tk.END, "正在加载评论，请稍候...")
        self.comment_text.config(state=tk.DISABLED)
        
        # 禁用加载更多按钮，直到加载完成
        self.load_more_btn.config(state=tk.DISABLED)
        
        # 在新线程中加载评论，避免UI卡顿
        threading.Thread(target=self._load_comments_thread, args=(False,), daemon=True).start()
    
    def load_more_comments(self):
        """加载更多评论（分页加载）"""
        if not self.current_song:
            messagebox.showwarning("提示", "请先播放一首歌曲")
            return
        
        # 检查是否还有更多评论
        if len(self.comments) >= self.total_comment_count:
            messagebox.showinfo("提示", "已经加载全部评论")
            return
        
        self.status_var.set(f"正在加载更多评论...({len(self.comments)}/{self.total_comment_count})")
        
        # 禁用加载按钮，防止重复点击
        self.load_comment_btn.config(state=tk.DISABLED)
        self.load_more_btn.config(state=tk.DISABLED)
        
        # 在新线程中加载更多评论
        threading.Thread(target=self._load_comments_thread, args=(True,), daemon=True).start()
    
    def _load_comments_thread(self, append):
        """后台线程加载评论"""
        song_id = self.current_song.get("id")
        new_comments, self.total_comment_count = self.get_comments(
            song_id, 
            offset=self.comment_offset, 
            limit=self.comment_limit
        )
        
        # 保存新加载的评论，用于显示
        self.new_comments = new_comments
        
        # 更新评论列表和偏移量
        if append:
            self.comments.extend(new_comments)
        else:
            self.comments = new_comments
        
        self.comment_offset += len(new_comments)
        
        # 在主线程中更新UI
        self.root.after(0, lambda: self.display_comments(append))
        self.root.after(0, lambda: self.status_var.set(
            f"已加载 {len(self.comments)}/{self.total_comment_count} 条评论"
        ))
        
        # 启用适当的按钮
        self.root.after(0, lambda: self.load_comment_btn.config(state=tk.NORMAL))
        
        # 如果还有更多评论，启用加载更多按钮
        if len(self.comments) < self.total_comment_count:
            self.root.after(0, lambda: self.load_more_btn.config(state=tk.NORMAL))
        else:
            self.root.after(0, lambda: self.load_more_btn.config(state=tk.DISABLED))
    
    def download_song_to_temp(self, song_url):
        """下载歌曲到临时文件并返回文件路径"""
        try:
            # 创建临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(temp_fd)  # 关闭文件描述符，以便其他程序可以打开它
            
            # 下载歌曲
            response = requests.get(song_url, stream=True, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*16):  # 16KB块
                    if chunk:
                        f.write(chunk)
            
            return temp_path
        except Exception as e:
            print(f"下载歌曲到临时文件失败: {str(e)}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return None
    
    def play_selected_song(self, event=None):
        """播放选中的歌曲"""
        selected_item = self.song_tree.selection()
        if not selected_item:
            messagebox.showwarning("提示", "请先选择一首歌曲")
            return
        
        index = int(self.song_tree.item(selected_item[0], "values")[0]) - 1
        self.current_index = index
        self.play_song(index)
    
    def stop_playback(self):
        """停止当前播放"""
        if self.use_alternative_player and hasattr(self, 'player_process') and self.player_process.poll() is None:
            self.player_process.terminate()
        else:
            pygame.mixer.music.stop()
        
        self.playing = False
        self.paused = False
        self.play_btn.config(text="播放")
    
    def play_song(self, index):
        """播放指定索引的歌曲，移除VIP限制检查"""
        if 0 <= index < len(self.playlist):
            try:
                song = self.playlist[index]
                
                # 停止当前播放
                self.stop_playback()
                
                # 清除之前的临时文件
                if self.temp_file and os.path.exists(self.temp_file):
                    try:
                        os.remove(self.temp_file)
                    except:
                        pass
                self.temp_file = None
                
                self.current_song = song
                
                # 更新当前播放信息
                song_name = song["name"]
                artists = "/".join([artist["name"] for artist in song["artists"]])
                self.now_playing_var.set(f"正在播放: {song_name} - {artists}")
                self.status_var.set(f"正在加载: {song_name}")
                
                # 启用评论按钮
                self.load_comment_btn.config(state=tk.NORMAL)
                self.load_more_btn.config(state=tk.DISABLED)  # 初始禁用加载更多
                
                # 重置评论相关变量
                self.comments = []
                self.comment_offset = 0
                self.total_comment_count = 0
                self.comment_count_var.set("评论数量: 0")
                
                # 获取歌词
                song_id = song["id"]
                self.lyrics = self.get_lyrics(song_id)
                self.display_lyrics()
                
                # 清空评论
                self.comments = []
                self.comment_text.config(state=tk.NORMAL)
                self.comment_text.delete(1.0, tk.END)
                self.comment_text.insert(tk.END, "点击下方按钮加载评论")
                self.comment_text.config(state=tk.DISABLED)
                
                # 获取并播放歌曲
                self.song_url = self.get_song_url(song_id)
                
                if self.song_url:
                    # 下载歌曲到临时文件
                    self.temp_file = self.download_song_to_temp(self.song_url)
                    if not self.temp_file:
                        messagebox.showerror("错误", "无法下载歌曲")
                        self.status_var.set("下载失败")
                        return
                    
                    # 获取歌曲时长（从API获取，更可靠）
                    self.total_length = song["duration"] // 1000  # 转换为秒
                    self.total_time_var.set(self.format_time(self.total_length))
                    
                    # 根据选择的模式播放歌曲
                    if self.use_alternative_player:
                        # 使用系统默认播放器
                        self.play_with_system_player()
                    else:
                        # 使用pygame播放
                        self.play_with_pygame()
                    
                    self.playing = True
                    self.paused = False
                    self.play_btn.config(text="暂停")
                    self.status_var.set(f"正在播放: {song_name}")
                    
                    # 启动进度更新线程
                    threading.Thread(target=self.update_progress, daemon=True).start()
                else:
                    messagebox.showerror("错误", "无法获取歌曲播放链接")
                    self.status_var.set("获取播放链接失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"播放失败: {str(e)}")
                self.status_var.set("播放失败")
    
    def play_with_pygame(self):
        """使用pygame播放音乐"""
        try:
            pygame.mixer.music.load(self.temp_file)
            pygame.mixer.music.play()
        except pygame.error as e:
            # 尝试修复MP3文件
            if "can't sync to MPEG frame" in str(e):
                messagebox.showwarning("格式警告", "检测到不标准的MP3格式，尝试修复...")
                self.convert_mp3(self.temp_file)
                pygame.mixer.music.load(self.temp_file)
                pygame.mixer.music.play()
            else:
                raise e
    
    def play_with_system_player(self):
        """使用系统默认播放器播放音乐"""
        try:
            if platform.system() == 'Windows':
                # Windows系统
                self.player_process = subprocess.Popen(['start', '', self.temp_file], shell=True)
            elif platform.system() == 'Darwin':
                # macOS系统
                self.player_process = subprocess.Popen(['open', self.temp_file])
            else:
                # Linux系统
                self.player_process = subprocess.Popen(['xdg-open', self.temp_file])
        except Exception as e:
            messagebox.showerror("错误", f"系统播放器启动失败: {str(e)}")
            # 自动切换回pygame模式并尝试播放
            self.use_alternative_player = False
            self.player_mode_var.set("默认播放器")
            self.play_with_pygame()
    
    def convert_mp3(self, file_path):
        """尝试修复/转换MP3文件以解决格式问题"""
        try:
            # 创建一个临时输出文件
            temp_fd, output_path = tempfile.mkstemp(suffix=".mp3")
            os.close(temp_fd)
            
            # 使用ffmpeg转换（需要系统安装ffmpeg）
            subprocess.run(
                ['ffmpeg', '-y', '-i', file_path, '-acodec', 'mp3', output_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 替换原始文件
            os.replace(output_path, file_path)
            return True
        except:
            # ffmpeg可能未安装，尝试其他方法
            try:
                # 简单的文件复制，有时也能解决问题
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # 尝试去除可能导致问题的ID3标签
                if content.startswith(b'ID3'):
                    # 跳过ID3v2标签
                    size_bytes = content[6:10]
                    size = 0
                    for byte in size_bytes:
                        size = (size << 7) | (byte & 0x7F)
                    content = content[10 + size:]
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                return True
            except Exception as e:
                print(f"MP3修复失败: {str(e)}")
                return False
    
    def toggle_play(self):
        """切换播放/暂停状态"""
        if not self.current_song:
            if self.playlist:
                self.current_index = 0
                self.play_song(0)
            else:
                messagebox.showwarning("提示", "请先搜索并选择歌曲")
            return
        
        if self.playing:
            if self.paused:
                # 继续播放
                if not self.use_alternative_player:
                    pygame.mixer.music.unpause()
                self.paused = False
                self.play_btn.config(text="暂停")
                self.status_var.set(f"正在播放: {self.current_song['name']}")
            else:
                # 暂停播放
                if not self.use_alternative_player:
                    pygame.mixer.music.pause()
                self.paused = True
                self.play_btn.config(text="播放")
                self.status_var.set(f"已暂停: {self.current_song['name']}")
        else:
            self.play_song(self.current_index)
    
    def play_next(self):
        """播放下一首"""
        if self.playlist and len(self.playlist) > 1:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.play_song(self.current_index)
    
    def play_previous(self):
        """播放上一首"""
        if self.playlist and len(self.playlist) > 1:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            self.play_song(self.current_index)
    
    def set_volume(self, value):
        """设置音量"""
        if not self.use_alternative_player:  # 系统播放器模式下无法控制音量
            volume = float(value) / 100
            pygame.mixer.music.set_volume(volume)
    
    def show_volume_dialog(self):
        """显示音量对话框"""
        if self.use_alternative_player:
            messagebox.showinfo("提示", "系统播放器模式下，请在系统播放器中调整音量")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("音量设置")
        dialog.geometry("300x100")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="调整音量:").pack(pady=10)
        
        volume_scale = ttk.Scale(dialog, from_=0, to=100, length=200)
        volume_scale.set(self.volume_var.get())
        volume_scale.pack()
        
        def apply_volume():
            self.volume_var.set(volume_scale.get())
            self.set_volume(volume_scale.get())
            dialog.destroy()
        
        ttk.Button(dialog, text="确定", command=apply_volume).pack(pady=10)
    
    def update_progress(self):
        """更新播放进度和歌词显示"""
        start_time = time.time()
        while self.playing and not self.paused:
            # 计算已播放时间
            elapsed = int(time.time() - start_time)
            
            # 检查播放是否结束
            if elapsed >= self.total_length:
                self.play_next()
                break
                
            # 更新进度条
            progress = (elapsed / self.total_length) * 100 if self.total_length > 0 else 0
            self.progress_var.set(progress)
            
            # 更新时间显示
            self.current_time_var.set(self.format_time(elapsed))
            
            # 更新歌词显示
            if not self.use_alternative_player:  # 系统播放器无法准确同步歌词
                self.update_lyric_display(elapsed)
            
            time.sleep(1)
    
    def set_progress(self, value):
        """设置播放进度"""
        if self.current_song and self.playing and self.total_length > 0:
            # 计算新位置
            new_position = (float(value) / 100) * self.total_length
            
            # 更新进度条和时间
            self.progress_var.set(value)
            self.current_time_var.set(self.format_time(int(new_position)))
            
            # 调整播放位置
            if not self.use_alternative_player:  # 系统播放器无法调整进度
                pygame.mixer.music.set_pos(new_position)
                
                # 调整进度计时器和歌词显示
                self.progress_start_time = time.time() - new_position
                self.update_lyric_display(new_position)
    
    def download_selected(self):
        """下载选中的歌曲，移除VIP限制检查"""
        selected_item = self.song_tree.selection()
        if not selected_item:
            messagebox.showwarning("提示", "请先选择一首歌曲")
            return
        
        index = int(self.song_tree.item(selected_item[0], "values")[0]) - 1
        song = self.playlist[index]
        
        try:
            song_id = song["id"]
            song_url = self.get_song_url(song_id)
            
            if not song_url:
                messagebox.showerror("错误", "无法获取歌曲下载链接")
                return
            
            # 获取保存路径
            song_name = song["name"]
            artists = "/".join([artist["name"] for artist in song["artists"]])
            default_filename = f"{song_name} - {artists}.mp3"
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if not save_path:
                return  # 用户取消保存
            
            # 下载歌曲
            self.status_var.set(f"正在下载: {song_name}")
            response = requests.get(song_url, stream=True)
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024*16  # 16KB
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 更新下载进度
                        progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                        self.status_var.set(f"正在下载: {song_name} ({progress:.1f}%)")
            
            self.status_var.set(f"下载完成: {song_name}")
            messagebox.showinfo("成功", f"歌曲已下载至:\n{save_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"下载失败: {str(e)}")
            self.status_var.set("下载失败")

    def on_close(self):
        """关闭窗口时清理临时文件"""
        # 停止播放
        self.stop_playback()
        
        # 清理临时文件
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NeteaseMusicPlayer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)  # 关闭窗口时清理
    root.mainloop()

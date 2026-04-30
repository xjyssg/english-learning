import tkinter as tk
from tkinter import messagebox
import random
import os
import re

# --- 配置区 ---
FILE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "生词本.md")
# -------------

# 视觉配置
MAIN_FONT_CN = ("Microsoft YaHei UI", 20, "bold") 
LEMMA_FONT_EN = ("Arial", 26, "bold")
TEXT_FONT = ("Microsoft YaHei UI", 13)
STATUS_FONT = ("Microsoft YaHei UI", 11)

COLOR_PALETTE = {
    'bg_main': '#F7FAFC',
    'bg_card': '#EBF8FF',
    'bg_wrong_mode': '#FFF5F5',
    'text_main': '#2D3748',
    'accent': '#319795',
    'wrong_red': '#E53E3E',
    'added_green': '#48BB78',
    'status_bar': '#EDF2F7',
    'sub_text': '#4A5568',
    'btn_inactive': '#E2E8F0',
    'btn_active': '#3182CE'  # 选中状态的蓝色
}

def strip_md(text):
    """移除简单的 Markdown 格式标记（目前仅处理加粗 **text**）"""
    return re.sub(r'\*\*(.+?)\*\*', r'\1', str(text))

def load_data(file_path):
    """解析器：按表格边界切分为多个 List"""
    if not os.path.exists(file_path): return []
    tables = []
    current_table = []
    in_table = False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('|'):
                    if not in_table:
                        in_table = True
                        current_table = []
                        tables.append(current_table)
                    if '---' not in line:
                        parts = [p.strip() for p in line.split('|') if p.strip()]
                        # 兼容新旧两种表头
                        if len(parts) >= 3 and "Lemma Form" not in parts[0] and "Standard Lemma" not in parts[0]:
                            current_table.append({'lemma': parts[0], 'sentence': parts[1], 'chinese': parts[2]})
                else:
                    in_table = False
    except Exception: return []
    return [t for t in tables if t]

class DynamicVocabApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini 动态词库复习系统 - 多档位版")
        self.root.geometry("1000x880")
        
        # --- 数据预加载 ---
        self.all_tables = load_data(FILE_NAME)
        if not self.all_tables:
            messagebox.showerror("错误", "未发现有效表格，请检查文件内容。")
            self.root.destroy()
            return
            
        self.current_days = 3  # 默认值
        self.wrong_set = []           
        self.is_wrong_mode = False
        self.has_re_marked = False     
        self.show_answer_mode = False
        self.scope_buttons = {} # 存储范围按钮引用以便变色

        self.setup_ui()
        self.init_pool(self.current_days)

    def init_pool(self, days):
        """核心：根据天数重置单词池"""
        self.current_days = days
        # 如果 days 为 0 代表全量
        if days == 0:
            tables_to_use = self.all_tables
        else:
            tables_to_use = self.all_tables[:days]
            
        self.full_pool = [word for table in tables_to_use for word in table]
        random.shuffle(self.full_pool)
        self.full_pool_idx = 0
        
        # 更新按钮 UI 状态
        for d, btn in self.scope_buttons.items():
            if d == days:
                btn.config(bg=COLOR_PALETTE['btn_active'], fg="white")
            else:
                btn.config(bg=COLOR_PALETTE['btn_inactive'], fg="black")
        
        self.update_ui()

    def setup_ui(self):
        self.root.configure(bg=COLOR_PALETTE['bg_main'])
        
        # 顶部状态
        self.status_frame = tk.Frame(self.root, bg=COLOR_PALETTE['status_bar'], height=45)
        self.status_frame.pack(fill="x")
        self.lbl_mode = tk.Label(self.status_frame, text="📍 模式：普通复习", font=STATUS_FONT, bg=COLOR_PALETTE['status_bar'])
        self.lbl_mode.pack(side="left", padx=20)
        self.lbl_wrong_count = tk.Label(self.status_frame, text="❌ 错题待消：0", font=STATUS_FONT, bg=COLOR_PALETTE['status_bar'], fg=COLOR_PALETTE['wrong_red'])
        self.lbl_wrong_count.pack(side="right", padx=20)

        self.lbl_progress = tk.Label(self.root, text="", font=STATUS_FONT, bg=COLOR_PALETTE['bg_main'])
        self.lbl_progress.pack(pady=(15, 5))

        # 单词展示区
        self.q_frame = tk.Frame(self.root, bg=COLOR_PALETTE['bg_card'], bd=1, relief="solid")
        self.q_frame.pack(pady=10, fill="x", padx=60)
        self.lbl_chinese = tk.Message(self.q_frame, text="", font=MAIN_FONT_CN, width=850, justify="center", bg=COLOR_PALETTE['bg_card'])
        self.lbl_chinese.pack(pady=40)

        self.a_frame = tk.Frame(self.root, bg=COLOR_PALETTE['bg_card'], bd=1, relief="solid")
        self.lbl_lemma = tk.Message(self.a_frame, text="", font=LEMMA_FONT_EN, fg=COLOR_PALETTE['accent'], width=850, justify="center", bg=COLOR_PALETTE['bg_card'])
        self.lbl_lemma.pack(pady=(25, 5))
        self.lbl_sentence = tk.Message(self.a_frame, text="", font=TEXT_FONT, width=850, fg=COLOR_PALETTE['sub_text'], justify="center", bg=COLOR_PALETTE['bg_card'])
        self.lbl_sentence.pack(pady=(5, 25))

        self.btn_action = tk.Button(self.root, text="查看答案 (Enter)", font=("Microsoft YaHei UI", 14, "bold"), 
                                    bg=COLOR_PALETTE['accent'], fg="white", relief="flat", padx=60, pady=12, command=self.handle_click)
        self.btn_action.pack(pady=20)

        # 功能区
        self.func_frame = tk.Frame(self.root, bg=COLOR_PALETTE['bg_main'])
        self.func_frame.pack(pady=10)
        self.btn_mark_wrong = tk.Button(self.func_frame, text="🚩 加入错题 (Space)", font=STATUS_FONT, bg="#FED7D7", relief="flat", width=20, command=self.add_or_retain_wrong)
        self.btn_mark_wrong.pack(side="left", padx=10)
        self.btn_switch_mode = tk.Button(self.func_frame, text="🔄 错题强化模式", font=STATUS_FONT, bg="#E2E8F0", relief="flat", width=15, command=self.toggle_mode)
        self.btn_switch_mode.pack(side="left", padx=10)

        # 范围选择区 (多档位)
        self.range_frame = tk.LabelFrame(self.root, text=" 复习范围选择 (切换将重置进度) ", font=STATUS_FONT, bg=COLOR_PALETTE['bg_main'], padx=10, pady=10)
        self.range_frame.pack(pady=20)
        
        days_options = [("近1天", 1), ("近3天", 3), ("近5天", 5), ("近7天", 7), ("全部复习", 0)]
        for text, val in days_options:
            btn = tk.Button(self.range_frame, text=text, font=STATUS_FONT, relief="flat", width=10, command=lambda v=val: self.change_scope_request(v))
            btn.pack(side="left", padx=5)
            self.scope_buttons[val] = btn

        self.root.bind('<Return>', lambda e: self.handle_click())
        self.root.bind('<space>', lambda e: self.add_or_retain_wrong())

    def change_scope_request(self, new_days):
        if self.is_wrong_mode:
            messagebox.showwarning("提示", "请先退出错题强化模式再切换范围。")
            return
        # 只有在已经开始复习且没复习完时才提示确认
        if 0 < self.full_pool_idx < len(self.full_pool):
            if not messagebox.askyesno("确认切换", "切换复习范围将重置当前进度，确认吗？"):
                return
        self.init_pool(new_days)

    def update_ui(self):
        self.has_re_marked = False 
        if not self.is_wrong_mode:
            if self.full_pool_idx >= len(self.full_pool):
                if self.wrong_set:
                    messagebox.showinfo("完成", "当前范围已过完，进入错题强化。")
                    self.toggle_mode(force_to_wrong=True)
                else:
                    messagebox.showinfo("完成", "复习完毕！")
                    self.root.destroy()
                return
            item = self.full_pool[self.full_pool_idx]
            scope_name = "全部" if self.current_days == 0 else f"近{self.current_days}天"
            self.lbl_progress.config(text=f"[{scope_name}] 进度: {self.full_pool_idx + 1} / {len(self.full_pool)}")
        else:
            if not self.wrong_set:
                messagebox.showinfo("提示", "错题本已清空！返回普通模式。")
                self.toggle_mode(force_to_normal=True)
                return
            item = self.wrong_set[0]
            self.lbl_progress.config(text=f"错题模式 - 剩余: {len(self.wrong_set)}")

        self.lbl_chinese.config(text=strip_md(item['chinese']))
        self.a_frame.pack_forget()
        self.btn_action.config(text="查看答案 (Enter)")
        self.show_answer_mode = False

        if not self.is_wrong_mode:
            is_in_wrong = any(w['lemma'] == item['lemma'] for w in self.wrong_set)
            self.btn_mark_wrong.config(text="✅ 已在错题本" if is_in_wrong else "🚩 加入错题 (Space)", 
                                       bg="#C6F6D5" if is_in_wrong else "#FED7D7", 
                                       state="disabled" if is_in_wrong else "normal")
        else:
            self.btn_mark_wrong.config(text="🔥 没记住,保留 (Space)", bg="#FEB2B2", state="normal")

    def add_or_retain_wrong(self, event=None):
        if str(self.btn_mark_wrong['state']) == 'disabled': return
        if not self.is_wrong_mode:
            item = self.full_pool[self.full_pool_idx]
            if not any(w['lemma'] == item['lemma'] for w in self.wrong_set):
                self.wrong_set.append(item)
                self.lbl_wrong_count.config(text=f"❌ 错题待消：{len(self.wrong_set)}")
                self.btn_mark_wrong.config(text="✅ 已加入", bg="#C6F6D5", state="disabled")
        else:
            self.has_re_marked = True
            self.btn_mark_wrong.config(text="♻️ 末尾重现确认", bg="#FBB6CE", state="disabled")

    def toggle_mode(self, force_to_wrong=False, force_to_normal=False):
        if (not self.is_wrong_mode or force_to_wrong) and not force_to_normal:
            if not self.wrong_set:
                messagebox.showinfo("提示", "错题本为空。")
                return
            self.is_wrong_mode = True
            self.lbl_mode.config(text="📍 模式：错题强化 (自动消除制)", fg=COLOR_PALETTE['wrong_red'])
            self.root.configure(bg=COLOR_PALETTE['bg_wrong_mode'])
        else:
            self.is_wrong_mode = False
            self.lbl_mode.config(text="📍 模式：普通复习", fg="black")
            self.root.configure(bg=COLOR_PALETTE['bg_main'])
        self.update_ui()

    def handle_click(self):
        if not self.show_answer_mode:
            item = self.wrong_set[0] if self.is_wrong_mode else self.full_pool[self.full_pool_idx]
            self.a_frame.pack(pady=10, fill="x", padx=60)
            self.lbl_lemma.config(text=strip_md(item['lemma']))
            self.lbl_sentence.config(text=f"📖 Example: {strip_md(item['sentence'])}")
            self.btn_action.config(text="下一题 (Enter)")
            self.show_answer_mode = True
        else:
            if self.is_wrong_mode:
                current_item = self.wrong_set.pop(0)
                if self.has_re_marked: self.wrong_set.append(current_item)
                self.lbl_wrong_count.config(text=f"❌ 错题待消：{len(self.wrong_set)}")
            else: self.full_pool_idx += 1
            self.update_ui()

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = tk.Tk()
    root.tk.call('tk', 'scaling', 1.5)
    app = DynamicVocabApp(root)
    root.mainloop()
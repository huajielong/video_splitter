import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
import tempfile
import threading
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频自动拼接与移动工具")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))
        
        # 变量初始化
        self.folder_a = tk.StringVar()
        self.folder_b = tk.StringVar()
        self.is_processing = False
        self.process_thread = None
        
        # 结果统计
        self.stats = {
            'successfully_spliced': 0,
            'directly_moved': 0,
            'deleted_corrupt': 0,
            'deleted_empty': 0,
            'retained_files': 0,
            'spliced_durations': [],
            'moved_durations': []
        }
        
        # 缓存目录
        self.cache_dir = os.path.join(tempfile.gettempdir(), "video_splitter_cache")
        
        # 清理历史临时文件
        self.cleanup_temp_files()
        
        # 创建UI
        self.create_ui()
    
    def create_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 路径选择区域
        path_frame = ttk.LabelFrame(main_frame, text="文件夹设置", padding="10")
        path_frame.pack(fill=tk.X, pady=10)
        
        # 文件夹A选择
        ttk.Label(path_frame, text="文件夹A（待处理视频源）:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(path_frame, textvariable=self.folder_a, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_folder_a).grid(row=0, column=2, padx=5, pady=5)
        
        # 文件夹B选择
        ttk.Label(path_frame, text="文件夹B（拼接后视频目标）:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(path_frame, textvariable=self.folder_b, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_folder_b).grid(row=1, column=2, padx=5, pady=5)
        
        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="终止处理", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        self.progress_var = tk.StringVar(value="准备就绪")
        progress_label = ttk.Label(main_frame, textvariable=self.progress_var, font=("SimHei", 10, "bold"))
        progress_label.pack(fill=tk.X, pady=10)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text="处理状态", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.status_text = tk.Text(status_frame, height=10, width=70, font=("SimHei", 10))
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.status_text.config(state=tk.DISABLED)
    
    def browse_folder_a(self):
        folder = filedialog.askdirectory(title="选择文件夹A（待处理视频源）")
        if folder:
            self.folder_a.set(folder)
    
    def browse_folder_b(self):
        folder = filedialog.askdirectory(title="选择文件夹B（拼接后视频目标）")
        if folder:
            self.folder_b.set(folder)
    
    def cleanup_temp_files(self):
        """清理历史临时文件，包括MoviePy生成的临时文件"""
        # 清理程序自己的缓存目录
        if os.path.exists(self.cache_dir):
            try:
                for file in os.listdir(self.cache_dir):
                    file_path = os.path.join(self.cache_dir, file)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                self.append_status("已清理程序缓存文件")
            except Exception as e:
                logger.error(f"清理缓存文件失败: {str(e)}")
        
        # 确保缓存目录存在
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # 清理MoviePy生成的临时文件（通常在当前工作目录）
        try:
            current_dir = os.getcwd()
            temp_files_count = 0
            
            # 查找并删除MoviePy临时文件（通常包含'TEMP_MPY'、'TEMP_MPY_mp'、'TEMP_MPY_snd'等标识）
            for file in os.listdir(current_dir):
                if ('TEMP_MPY' in file and file.endswith('.mp4')) or ('TEMP_MPY' in file and file.endswith('.wav')):
                    try:
                        os.unlink(os.path.join(current_dir, file))
                        temp_files_count += 1
                    except:
                        pass  # 如果无法删除，继续处理下一个文件
                        
            if temp_files_count > 0:
                self.append_status(f"已清理 {temp_files_count} 个MoviePy临时文件")
        except Exception as e:
            logger.error(f"清理MoviePy临时文件失败: {str(e)}")
    
    def start_processing(self):
        """开始处理视频文件"""
        # 检查文件夹路径
        folder_a = self.folder_a.get().strip()
        folder_b = self.folder_b.get().strip()
        
        if not folder_a or not folder_b:
            messagebox.showerror("错误", "请选择文件夹A和文件夹B")
            return
        
        # 检查文件夹是否存在，不存在则创建
        if not os.path.exists(folder_a):
            if messagebox.askyesno("提示", "所选文件夹A不存在，是否自动创建？"):
                try:
                    os.makedirs(folder_a)
                except Exception as e:
                    messagebox.showerror("错误", f"创建文件夹A失败: {str(e)}")
                    return
            else:
                return
        
        if not os.path.exists(folder_b):
            if messagebox.askyesno("提示", "所选文件夹B不存在，是否自动创建？"):
                try:
                    os.makedirs(folder_b)
                except Exception as e:
                    messagebox.showerror("错误", f"创建文件夹B失败: {str(e)}")
                    return
            else:
                return
        
        # 检查文件夹A中是否有MP4文件
        mp4_files = [f for f in os.listdir(folder_a) if f.lower().endswith('.mp4')]
        if not mp4_files:
            messagebox.showinfo("提示", "当前文件夹A中无MP4格式视频，请重新选择")
            return
        
        # 重置统计信息
        self.stats = {
            'successfully_spliced': 0,
            'directly_moved': 0,
            'deleted_corrupt': 0,
            'deleted_empty': 0,
            'retained_files': 0,
            'spliced_durations': [],
            'moved_durations': []
        }
        
        # 清空状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_processing = True
        
        # 在新线程中处理视频
        self.process_thread = threading.Thread(target=self.process_videos, args=(folder_a, folder_b))
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def stop_processing(self):
        """停止处理视频文件"""
        self.is_processing = False
        self.append_status("正在停止处理...")
        
        # 如果线程存在且正在运行，等待它结束
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=5.0)  # 等待最多5秒
        
        self.append_status("处理已停止")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set("处理已停止")
    
    def process_videos(self, folder_a, folder_b):
        """处理视频的核心逻辑"""
        try:
            # 1. 获取并过滤MP4文件
            mp4_files = [f for f in os.listdir(folder_a) if f.lower().endswith('.mp4')]
            self.update_progress(f"找到 {len(mp4_files)} 个MP4文件")
            
            # 2. 排序文件
            self.update_progress("正在排序文件...")
            sorted_files = self.sort_files(folder_a, mp4_files)
            
            # 3. 处理文件
            self.process_files(folder_a, folder_b, sorted_files)
            
            # 4. 显示结果汇总
            self.show_summary()
            
        except Exception as e:
            logger.error(f"处理视频时发生错误: {str(e)}")
            self.append_status(f"错误: {str(e)}")
            messagebox.showerror("错误", f"处理视频时发生错误: {str(e)}")
        finally:
            # 清理临时文件
            self.cleanup_temp_files()
            
            # 恢复按钮状态
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.progress_var.set("处理完成"))
            self.is_processing = False
    
    def sort_files(self, folder_path, files):
        """按文件名中的日期信息排序文件"""
        def get_file_date(file_name):
            # 尝试从文件名中提取日期
            date_patterns = [
                r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
                r'(\d{4})-(\d{2})-(\d{2})'  # YYYY-MM-DD
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, file_name)
                if match:
                    try:
                        if len(match.groups()) == 3:
                            # YYYYMMDD 或 YYYY-MM-DD 格式
                            year, month, day = match.groups()
                            return datetime.datetime(int(year), int(month), int(day)), file_name
                    except ValueError:
                        pass
            
            # 如果没有找到日期，返回一个很早的日期，让文件按系统默认顺序排序
            return datetime.datetime(1900, 1, 1), file_name
        
        # 排序文件：日期最新的在前，如果没有日期则按系统默认顺序
        sorted_files = sorted(files, key=get_file_date, reverse=True)
        
        # 更新进度
        self.update_progress(f"文件排序完成，共 {len(sorted_files)} 个文件")
        return sorted_files
    
    def process_files(self, folder_a, folder_b, sorted_files):
        """处理排序后的文件"""
        current_batch = []
        current_duration = 0
        
        # 用于跟踪已处理的文件，防止重复处理
        processed_files = set()
        
        # 创建一个副本以便能够安全地修改正在迭代的列表
        files_to_process = sorted_files.copy()
        
        for i in range(len(files_to_process)):
            if not self.is_processing:
                break
            
            # 重新获取当前文件，因为列表可能已被修改
            if i >= len(files_to_process):
                break
            
            file_name = files_to_process[i]
            
            # 跳过已处理的文件
            if file_name in processed_files:
                continue
            
            file_path = os.path.join(folder_a, file_name)
            
            try:
                # 检查文件是否仍然存在（可能在上次运行中已被删除）
                if not os.path.exists(file_path):
                    self.append_status(f"文件不存在: {file_name}")
                    processed_files.add(file_name)
                    continue
                
                # 获取视频时长
                video_clip = VideoFileClip(file_path)
                duration = video_clip.duration
                video_clip.close()
                
                # 检查是否为空文件
                if duration <= 0:
                    self.append_status(f"删除空文件: {file_name}")
                    os.remove(file_path)
                    self.stats['deleted_empty'] += 1
                    processed_files.add(file_name)  # 标记为已处理
                    continue
                
                # 检查单个视频是否满足时长要求
                if duration >= 60:
                    # 直接移动
                    if self.move_single_video(file_path, folder_b, file_name, duration):
                        processed_files.add(file_name)  # 标记为已处理
                else:
                    # 加入拼接批次
                    current_batch.append((file_path, file_name, duration))
                    current_duration += duration
                    
                    # 检查是否满足拼接条件
                    if current_duration >= 60:
                        # 拼接视频，并获取成功处理的文件列表
                        processed_batch = self.splice_videos(folder_b, current_batch, current_duration)
                        
                        # 标记批次中的文件为已处理
                        for _, batch_file_name, _ in processed_batch:
                            processed_files.add(batch_file_name)
                        
                        # 清空当前批次
                        current_batch = []
                        current_duration = 0
                        
            except Exception as e:
                # 处理异常文件
                self.append_status(f"删除损坏文件: {file_name} (错误: {str(e)})")
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass  # 如果无法删除，继续处理下一个文件
                
                self.stats['deleted_corrupt'] += 1
                processed_files.add(file_name)  # 标记为已处理
                continue
        
        # 处理剩余未拼接的文件
        self.stats['retained_files'] = len(current_batch)
        
        self.append_status(f"总处理文件数: {len(processed_files)}, 剩余未处理文件数: {self.stats['retained_files']}")
        
    def move_single_video(self, file_path, folder_b, file_name, duration):
        """直接移动单个视频文件
        
        返回: True 如果移动成功，False 如果移动失败
        """
        if not self.is_processing:
            return False
        
        try:
            # 处理文件名中的特殊字符
            safe_file_name = self.sanitize_filename(file_name)
            target_path = os.path.join(folder_b, safe_file_name)
            
            # 移动文件（覆盖已存在的文件）
            shutil.copy2(file_path, target_path)
            
            self.append_status(f"直接移动: {file_name} (时长: {duration:.1f}秒)")
            self.stats['directly_moved'] += 1
            self.stats['moved_durations'].append(duration)
            self.update_progress(f"已移动 {self.stats['directly_moved']} 个视频至文件夹B")
            
            return True
        except Exception as e:
            logger.error(f"移动文件 {file_name} 失败: {str(e)}")
            self.append_status(f"移动失败: {file_name} (错误: {str(e)})")
            return False
    
    def splice_videos(self, folder_b, batch, total_duration):
        """拼接视频文件
        
        返回: 成功处理的文件列表，用于标记为已处理
        """
        if not self.is_processing:
            return []
        
        # 用于存储成功处理的文件
        successfully_processed = []
        
        try:
            # 更新进度
            file_names = [f[1] for f in batch]
            self.update_progress(f"正在拼接: {'+'.join([f[:10]+'...' if len(f)>10 else f for f in file_names])}")
            
            # 拼接视频
            clips = []
            valid_files = []
            
            for file_path, file_name, duration in batch:
                try:
                    # 再次检查文件是否存在
                    if not os.path.exists(file_path):
                        self.append_status(f"文件不存在: {file_name}")
                        continue
                    
                    clip = VideoFileClip(file_path)
                    clips.append(clip)
                    valid_files.append((file_path, file_name, duration))
                except Exception as e:
                    logger.error(f"加载视频 {file_name} 失败: {str(e)}")
                    self.append_status(f"加载失败: {file_name} (错误: {str(e)})")
                    
                    # 尝试删除加载失败的文件
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            self.append_status(f"删除加载失败的文件: {file_name}")
                            self.stats['deleted_corrupt'] += 1
                    except:
                        pass  # 如果无法删除，继续处理下一个文件
            
            if not clips:
                self.append_status("没有有效的视频文件可拼接")
                return successfully_processed
            
            try:
                # 拼接视频，使用最后一个视频的属性
                final_clip = concatenate_videoclips(clips)
                
                # 生成拼接后的文件名
                # 改进：限制文件名长度，避免过长导致FFMPEG错误
                max_filename_length = 200  # 限制文件名最大长度
                
                # 获取基础文件名并处理特殊字符
                base_names = [os.path.splitext(f[1])[0] for f in valid_files]
                safe_base_names = [self.sanitize_filename(name) for name in base_names]
                
                # 计算每个文件名可以保留的最大长度
                if len(safe_base_names) > 1:
                    # 有多个文件时，每个文件名只保留前几个字符
                    max_part_length = max(10, min(30, max_filename_length // (len(safe_base_names) + 1) - 4))
                    short_names = [name[:max_part_length] if len(name) > max_part_length else name for name in safe_base_names]
                    output_file_name = '+'.join(short_names) + '.mp4'
                else:
                    # 只有一个文件时，保留原始名称
                    output_file_name = safe_base_names[0] + '.mp4'
                
                # 确保文件名不会过长
                if len(output_file_name) > max_filename_length:
                    base_part = output_file_name[:max_filename_length-10]
                    extension = '.mp4'
                    output_file_name = base_part + '...' + extension
                
                output_path = os.path.join(folder_b, output_file_name)
                
                # 保存拼接后的视频
                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
                
                # 关闭所有视频
                final_clip.close()
                for clip in clips:
                    clip.close()
                
                self.append_status(f"成功拼接: {output_file_name} (总时长: {total_duration:.1f}秒)")
                self.stats['successfully_spliced'] += 1
                self.stats['spliced_durations'].append(total_duration)
                self.update_progress(f"已拼接 {self.stats['successfully_spliced']} 个视频序列")
                
                # 记录成功处理的文件
                successfully_processed = valid_files
                
                # 可选：删除已成功拼接的原始文件（如果用户希望清理源文件夹）
                # 注意：取消注释下面的代码将删除源文件夹中的原始视频文件
                # for file_path, _, _ in valid_files:
                #     try:
                #         os.remove(file_path)
                #         self.append_status(f"已删除源文件: {os.path.basename(file_path)}")
                #     except Exception as e:
                #         logger.error(f"删除源文件 {os.path.basename(file_path)} 失败: {str(e)}")
                
            except Exception as e:
                logger.error(f"拼接视频失败: {str(e)}")
                self.append_status(f"拼接失败: {str(e)}")
                
        finally:
            # 确保关闭所有视频
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
        
        return successfully_processed
    
    def sanitize_filename(self, filename):
        """过滤文件名中的特殊字符"""
        # Windows系统不允许的字符
        invalid_chars = '<>:/\\|?*"'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        return filename
    
    def update_progress(self, message):
        """更新进度显示"""
        self.root.after(0, lambda: self.progress_var.set(message))
    
    def append_status(self, message):
        """追加状态信息"""
        self.root.after(0, lambda:
            [
                self.status_text.config(state=tk.NORMAL),
                self.status_text.insert(tk.END, message + "\n"),
                self.status_text.see(tk.END),
                self.status_text.config(state=tk.DISABLED)
            ]
        )
    
    def show_summary(self):
        """显示处理结果汇总"""
        summary = "处理完成！\n"
        summary += f"- 成功拼接：{self.stats['successfully_spliced']}个视频（总时长分别为{', '.join([f'{d:.0f}秒' for d in self.stats['spliced_durations']])}），已移动至文件夹B\n"
        summary += f"- 直接移动：{self.stats['directly_moved']}个视频（时长{', '.join([f'{d:.0f}秒' for d in self.stats['moved_durations']])}），已移动至文件夹B\n"
        summary += f"- 异常处理：删除{self.stats['deleted_corrupt']}个损坏文件、{self.stats['deleted_empty']}个空文件\n"
        summary += f"- 保留文件：{self.stats['retained_files']}个视频，保留在文件夹A\n"
        
        self.root.after(0, lambda: messagebox.showinfo("处理结果", summary))

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoSplitterApp(root)
    
    # 捕获窗口关闭事件
    def on_closing():
        if app.is_processing:
            if messagebox.askyesno("提示", "处理正在进行中，确定要关闭窗口吗？"):
                app.stop_processing()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
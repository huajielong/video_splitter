import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime
import tempfile
import threading
import logging
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入moviepy库
HAS_MOVIEPY = False
try:
    import moviepy
    logger.info(f"moviepy版本: {moviepy.__version__}")
    
    # 根据探索脚本的结果，使用moviepy 2.1.2版本的正确导入路径
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
    
    # 注意：在这个版本中，resize是大写的Resize
    try:
        from moviepy.video.fx.Resize import Resize as resize
        logger.info("成功导入Resize工具")
    except ImportError:
        # 尝试另一种可能的导入方式
        from moviepy.video.fx.resize import resize
        logger.info("成功导入resize工具")
        
    from moviepy.video.VideoClip import ColorClip
    
    HAS_MOVIEPY = True
    logger.info("成功导入所有必要的moviepy模块")
    
except ImportError as e:
    logger.error(f"无法导入moviepy库: {str(e)}")
    try:
        # 显示更详细的错误信息
        import sys
        print(f"错误详情: {str(e)}")
        print(f"Python版本: {sys.version}")
        print(f"当前目录: {os.getcwd()}")
    except:
        pass

class VideoSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频自动拼接与移动工具")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))
        
        # 变量初始化
        self.folder_a = tk.StringVar()
        self.folder_b = tk.StringVar()
        self.target_duration = tk.StringVar(value="60")
        self.delete_source = tk.BooleanVar(value=False)
        self.dont_ask_again = False
        self.is_processing = False
        self.process_thread = None
        self.temp_dir = None
        
        # 结果统计
        self.stats = {
            'successfully_spliced': 0,
            'directly_moved': 0,
            'deleted_corrupt': 0,
            'deleted_empty': 0,
            'deleted_failed_preprocess': 0,
            'retained_files': 0,
            'deleted_source_files': 0,
            'spliced_durations': [],
            'moved_durations': [],
            'preprocessed_files': 0,
            'target_duration': 60
        }
        
        # 清理历史临时文件
        self.cleanup_temp_files()
        
        # 创建UI界面
        self.create_ui()
    
    def create_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件夹配置区域
        folder_frame = ttk.LabelFrame(main_frame, text="文件夹配置", padding="10")
        folder_frame.pack(fill=tk.X, pady=10)
        
        # 文件夹A
        ttk.Label(folder_frame, text="文件夹A (视频源):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.folder_a, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(folder_frame, text="浏览", command=self.browse_folder_a).grid(row=0, column=2, padx=5, pady=5)
        
        # 文件夹B
        ttk.Label(folder_frame, text="文件夹B (目标):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.folder_b, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(folder_frame, text="浏览", command=self.browse_folder_b).grid(row=1, column=2, padx=5, pady=5)
        
        # 拼接参数设置区域
        params_frame = ttk.LabelFrame(main_frame, text="拼接参数设置", padding="10")
        params_frame.pack(fill=tk.X, pady=10)
        
        # 目标时长
        ttk.Label(params_frame, text="目标拼接时长 (10-3600秒):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(params_frame, textvariable=self.target_duration, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        # 快捷选项
        quick_frame = ttk.Frame(params_frame)
        quick_frame.grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(quick_frame, text="60秒", command=lambda: self.set_duration(60)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="120秒", command=lambda: self.set_duration(120)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="180秒", command=lambda: self.set_duration(180)).pack(side=tk.LEFT, padx=2)
        
        # 删除源文件选项
        delete_frame = ttk.Frame(params_frame)
        delete_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Checkbutton(delete_frame, text="拼接成功后删除文件夹A中的原视频", variable=self.delete_source, 
                       command=self.on_delete_source_toggled).pack(side=tk.LEFT)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.progress_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor=tk.W, pady=5)
        
        # 状态文本框
        self.status_text = tk.Text(progress_frame, height=15, width=80, wrap=tk.WORD, state=tk.DISABLED)
        self.status_text.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
    
    def browse_folder_a(self):
        folder = filedialog.askdirectory(title="选择文件夹A (视频源)")
        if folder:
            self.folder_a.set(folder)
    
    def browse_folder_b(self):
        folder = filedialog.askdirectory(title="选择文件夹B (目标)")
        if folder:
            self.folder_b.set(folder)
        else:
            # 如果用户没有选择文件夹，询问是否创建
            if messagebox.askyesno("提示", "文件夹不存在，是否自动创建？"):
                # 这里应该处理用户输入的路径，但tkinter的askdirectory不会返回不存在的路径
                # 所以这个逻辑需要调整
                pass
    
    def set_duration(self, duration):
        self.target_duration.set(str(duration))
    
    def on_delete_source_toggled(self):
        if self.delete_source.get() and not self.dont_ask_again:
            response = messagebox.askyesnocancel("警告", "删除后无法恢复，是否继续？", 
                                               icon=messagebox.WARNING)
            if response is None:  # 取消操作
                self.delete_source.set(False)
            elif response is False:  # 不继续
                self.delete_source.set(False)
            else:  # 继续并记住选择
                if messagebox.askyesno("提示", "不再提示此警告？"):
                    self.dont_ask_again = True
    
    def validate_inputs(self):
        # 检查文件夹A和B是否选择
        if not self.folder_a.get():
            messagebox.showerror("错误", "请选择文件夹A")
            return False
        
        if not self.folder_b.get():
            messagebox.showerror("错误", "请选择文件夹B")
            return False
        
        # 检查文件夹是否存在，不存在则创建
        for folder_path in [self.folder_a.get(), self.folder_b.get()]:
            if not os.path.exists(folder_path):
                if messagebox.askyesno("提示", f"文件夹 '{folder_path}' 不存在，是否自动创建？"):
                    try:
                        os.makedirs(folder_path)
                    except Exception as e:
                        messagebox.showerror("错误", f"创建文件夹失败: {str(e)}")
                        return False
                else:
                    return False
        
        # 检查目标时长
        try:
            duration = int(self.target_duration.get())
            if duration < 10 or duration > 3600:
                messagebox.showerror("错误", "请输入10-3600秒内的有效数字")
                return False
            self.stats['target_duration'] = duration
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return False
        
        # 检查文件夹A中是否有MP4文件
        mp4_files = [f for f in os.listdir(self.folder_a.get()) if f.lower().endswith('.mp4')]
        if not mp4_files:
            messagebox.showerror("错误", "文件夹A中无MP4格式视频，请重新选择")
            return False
        
        return True
    
    def start_processing(self):
        if not self.validate_inputs():
            return
        
        self.is_processing = True
        self.start_button.config(state=tk.DISABLED)
        
        # 重置统计信息
        self.stats = {
            'successfully_spliced': 0,
            'directly_moved': 0,
            'deleted_corrupt': 0,
            'deleted_empty': 0,
            'deleted_failed_preprocess': 0,
            'retained_files': 0,
            'deleted_source_files': 0,
            'spliced_durations': [],
            'moved_durations': [],
            'preprocessed_files': 0,
            'target_duration': int(self.target_duration.get())
        }
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"创建临时目录: {self.temp_dir}")
        
        # 清空状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # 在新线程中开始处理
        self.process_thread = threading.Thread(target=self.process_videos)
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def stop_processing(self):
        # 由于用户不需要终止处理功能，此方法已被禁用
        # 设置终止标志
        self.is_processing = False
        self.append_status("正在终止处理...")
        
        # 等待线程结束，但设置超时时间（最多等待5秒）
        if self.process_thread and self.process_thread.is_alive():
            self.append_status("等待处理线程结束...")
            # 最多等待5秒让线程自然结束
            timeout = 5.0
            start_time = time.time()
            
            # 定期检查线程状态，直到线程结束或超时
            while self.process_thread.is_alive() and (time.time() - start_time) < timeout:
                time.sleep(0.1)  # 短暂休眠以避免CPU占用过高
            
            # 如果线程仍然在运行，记录警告
            if self.process_thread.is_alive():
                self.append_status("警告：处理线程可能仍在后台运行，可能需要手动关闭程序")
                logger.warning("处理线程未能在超时时间内终止")
        
        # 更新UI状态
        self.update_progress("已终止处理")
        self.start_button.config(state=tk.NORMAL)
        
        # 清理临时文件
        self.cleanup_temp_files()
        self.append_status("临时文件已清理")
    
    def process_videos(self):
        try:
            # 1. 预处理视频
            canvas_files = self.preprocess_videos()
            
            if not canvas_files:
                self.update_progress("没有成功预处理的视频")
                self.root.after(0, lambda: messagebox.showinfo("提示", "文件夹A中无有效MP4格式视频或所有视频预处理失败"))
                self.root.after(0, self.finish_processing)
                return
            
            # 2. 排序画布版视频
            self.update_progress("正在排序画布版视频")
            self.append_status("正在排序画布版视频...")
            sorted_files = self.sort_videos(canvas_files)
            
            # 3. 拼接视频
            self.update_progress("正在拼接视频")
            self.append_status("开始拼接视频...")
            self.splice_videos(sorted_files)
            
            # 4. 显示结果汇总
            self.root.after(0, self.show_summary)
            
        except Exception as e:
            logger.error(f"处理过程中发生错误: {str(e)}")
            self.append_status(f"错误: {str(e)}")
        finally:
            # 清理临时文件
            self.cleanup_temp_files()
            self.root.after(0, self.finish_processing)
    
    def preprocess_videos(self):
        mp4_files = [f for f in os.listdir(self.folder_a.get()) if f.lower().endswith('.mp4')]
        canvas_files = []
        total_files = len(mp4_files)
        
        for i, filename in enumerate(mp4_files):
            if not self.is_processing:
                break
            
            file_path = os.path.join(self.folder_a.get(), filename)
            self.update_progress(f"正在预处理视频 ({i+1}/{total_files})")
            self.append_status(f"预处理视频: {filename}")
            
            try:
                # 检查视频是否损坏
                clip = VideoFileClip(file_path)
                duration = clip.duration
                clip.close()
                
                # 检查时长是否为0
                if duration <= 0:
                    self.append_status(f"文件时长为0，删除: {filename}")
                    os.remove(file_path)
                    self.stats['deleted_empty'] += 1
                    continue
                
                # 预处理：生成9:16黑色画布+画中画
                canvas_file = self.create_canvas_video(file_path, filename)
                if canvas_file:
                    canvas_files.append((canvas_file, file_path, duration))
                    self.stats['preprocessed_files'] += 1
                else:
                    self.append_status(f"预处理失败，删除: {filename}")
                    os.remove(file_path)
                    self.stats['deleted_failed_preprocess'] += 1
                    
            except Exception as e:
                self.append_status(f"文件损坏，删除: {filename} ({str(e)})")
                try:
                    os.remove(file_path)
                    self.stats['deleted_corrupt'] += 1
                except:
                    pass
        
        # 检查是否有预处理失败的视频
        if self.stats['deleted_failed_preprocess'] > 0:
            self.root.after(0, lambda: messagebox.showinfo("提示", 
                          f"检测到{self.stats['deleted_failed_preprocess']}个视频无法生成画布版，已自动删除"))
        
        return canvas_files
    
    def create_canvas_video(self, video_path, filename):
        try:
            # 画布尺寸：1080x1920（9:16）
            canvas_width, canvas_height = 1080, 1920
            
            # 加载原视频
            video = VideoFileClip(video_path)
            duration = video.duration
            
            # 计算调整后的尺寸（保持原比例）
            orig_width, orig_height = video.size
            ratio = min(canvas_width / orig_width, canvas_height / orig_height)
            new_width = int(orig_width * ratio)
            new_height = int(orig_height * ratio)
            
            # 计算居中位置
            x_pos = (canvas_width - new_width) // 2
            y_pos = (canvas_height - new_height) // 2
            
            # 由于moviepy 2.1.2版本中CompositeVideoClip和Resize存在兼容性问题，
            # 我们采用更简单的方法：直接使用ffmpeg命令行工具来实现视频合成
            # 输出文件名
            base_name = os.path.splitext(filename)[0]
            safe_name = self.filter_filename(f"{base_name}_画布版")
            output_path = os.path.join(self.temp_dir, f"{safe_name}.mp4")
            
            # 使用ffmpeg命令行工具来创建9:16画布并将原视频居中放置
            # 这种方法可以避免使用moviepy中存在兼容性问题的API
            import subprocess
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-f', 'lavfi', '-i', f'color=c=black:s={canvas_width}x{canvas_height}:d={duration}',
                '-filter_complex', f'[0:v]scale={new_width}:{new_height}[v1];[1:v][v1]overlay={x_pos}:{y_pos}[v]',
                '-map', '[v]', '-map', '0:a',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest',
                output_path
            ]
            
            # 执行ffmpeg命令
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 关闭视频
            video.close()
            
            return output_path
        except Exception as e:
            logger.error(f"创建画布视频失败: {str(e)}")
            return None
    
    def sort_videos(self, canvas_files):
        # 提取文件名和原路径
        file_info = []
        
        for canvas_file, orig_path, duration in canvas_files:
            filename = os.path.basename(canvas_file)
            
            # 尝试提取日期
            date = None
            # 尝试匹配YYYY-MM-DD格式
            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
            if not date_match:
                # 尝试匹配YYYYMMDD格式
                date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
            
            if date_match:
                try:
                    if len(date_match.groups()) == 3:
                        year, month, day = map(int, date_match.groups())
                        date = datetime.date(year, month, day)
                except:
                    pass
            
            # 获取视频分辨率
            try:
                clip = VideoFileClip(canvas_file)
                width, height = clip.size
                clip.close()
            except:
                width, height = 0, 0
            
            file_info.append((canvas_file, orig_path, duration, date, filename, width * height))
        
        # 排序：先按日期，再按文件名，最后按分辨率
        file_info.sort(key=lambda x: (x[3] if x[3] else datetime.date.max, x[4], -x[5]))
        
        return file_info
    
    def splice_videos(self, sorted_files):
        target_duration = self.stats['target_duration']
        current_sequence = []
        current_duration = 0
        source_files_to_delete = set()
        
        # 检查所有视频总时长是否小于目标时长
        total_duration = sum([duration for _, _, duration, _, _, _ in sorted_files])
        if total_duration < target_duration:
            self.append_status(f"所有视频总时长({total_duration:.1f}秒)小于目标时长({target_duration}秒)，不进行拼接")
            self.stats['retained_files'] = len(sorted_files)
            return
        
        # 处理每个视频
        i = 0
        while i < len(sorted_files):
            if not self.is_processing:
                break
            
            canvas_file, orig_path, duration, _, filename, _ = sorted_files[i]
            
            # 如果单个视频时长≥目标时长，直接移动
            if duration >= target_duration:
                self.append_status(f"视频时长({duration:.1f}秒)≥目标时长，直接移动: {filename}")
                
                # 构建目标文件名
                safe_name = self.filter_filename(os.path.splitext(filename)[0])
                target_path = os.path.join(self.folder_b.get(), f"{safe_name}.mp4")
                
                # 复制文件
                shutil.copy2(canvas_file, target_path)
                
                # 记录统计信息
                self.stats['directly_moved'] += 1
                self.stats['moved_durations'].append(duration)
                
                # 如果需要删除源文件
                if self.delete_source.get():
                    source_files_to_delete.add(orig_path)
                    
                i += 1
            else:
                # 开始一个新的拼接序列
                current_sequence = [sorted_files[i]]
                current_duration = duration
                i += 1
                
                # 添加后续视频直到达到目标时长
                while i < len(sorted_files) and current_duration < target_duration:
                    if not self.is_processing:
                        break
                    
                    canvas_file_next, orig_path_next, duration_next, _, filename_next, _ = sorted_files[i]
                    current_sequence.append(sorted_files[i])
                    current_duration += duration_next
                    
                    self.update_progress(f"正在拼接：{os.path.basename(current_sequence[0][0])}+...（当前时长：{current_duration:.0f}秒/目标{target_duration}秒）")
                    
                    i += 1
                
                # 确保参与拼接的视频均被使用
                if current_duration >= target_duration:
                    # 优先选择分辨率最高的视频作为最后一个
                    current_sequence.sort(key=lambda x: -x[5])  # 按分辨率从高到低排序
                    
                    # 在开始拼接前再次检查终止标志
                    if not self.is_processing:
                        self.append_status("处理已终止，取消当前视频序列的拼接")
                        break
                    
                    # 拼接视频
                    self.append_status(f"开始拼接视频序列（总时长：{current_duration:.1f}秒）")
                    
                    processing_aborted = False
                    final_clip = None
                    clips = []
                    try:
                        # 加载所有视频文件
                        for canvas_file_seq, _, _, _, _, _ in current_sequence:
                            # 加载每个视频文件前检查终止标志
                            if not self.is_processing:
                                self.append_status("处理已终止，取消视频加载")
                                processing_aborted = True
                                break
                            
                            clip = VideoFileClip(canvas_file_seq)
                            clips.append(clip)
                        
                        # 如果处理被终止，跳过后续操作
                        if processing_aborted or not self.is_processing:
                            continue
                        
                        # 拼接视频
                        final_clip = concatenate_videoclips(clips)
                        
                        # 构建输出文件名
                        base_names = [os.path.splitext(os.path.basename(f[0]))[0] for f in current_sequence]
                        safe_name = self.filter_filename("+".join(base_names))
                        output_path = os.path.join(self.folder_b.get(), f"{safe_name}.mp4")
                        
                        # 在开始写入前再次检查终止标志
                        if not self.is_processing:
                            self.append_status("处理已终止，取消视频写入")
                            processing_aborted = True
                        
                        # 保存拼接后的视频
                        if not processing_aborted:
                            final_clip.write_videofile(output_path, codec="libx264", fps=30, audio_codec="aac")
                        
                        # 记录统计信息
                        if not processing_aborted:
                            self.stats['successfully_spliced'] += 1
                            self.stats['spliced_durations'].append(current_duration)
                        
                        # 如果需要删除源文件
                        if not processing_aborted and self.delete_source.get():
                            for _, orig_path_seq, _, _, _, _ in current_sequence:
                                source_files_to_delete.add(orig_path_seq)
                        
                    except Exception as e:
                        self.append_status(f"拼接视频时出错: {str(e)}")
                        self.logger.error(f"拼接视频时出错: {str(e)}")
                    finally:
                        # 确保关闭所有视频资源
                        if final_clip:
                            final_clip.close()
                        for clip in clips:
                            clip.close()
        
        # 删除标记的源文件
        for source_file in source_files_to_delete:
            try:
                if os.path.exists(source_file):
                    os.remove(source_file)
                    self.stats['deleted_source_files'] += 1
            except Exception as e:
                self.append_status(f"删除源文件失败: {source_file} ({str(e)})")
    
    def filter_filename(self, filename):
        # 过滤文件名中的特殊字符
        # Windows系统不允许的字符
        invalid_chars = '<>:/\|?*"'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        
        # 限制文件名长度，确保加上路径后不会超过Windows 260字符的路径长度限制
        # 预留100字符给路径，文件名限制在150字符以内
        max_filename_length = 150
        if len(filename) > max_filename_length:
            # 计算需要保留的后缀长度（如果有的话）
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) > 1:
                base_name, ext = name_parts
                # 确保扩展名不会丢失
                ext = '.' + ext if not ext.startswith('.') else ext
                # 为扩展名预留空间
                base_name = base_name[:max_filename_length - len(ext)]
                filename = base_name + ext
            else:
                filename = filename[:max_filename_length]
        
        return filename
    
    def update_progress(self, message):
        # 更新进度显示
        self.root.after(0, lambda: self.progress_var.set(message))
    
    def append_status(self, message):
        # 追加状态信息
        self.root.after(0, lambda: 
            [
                self.status_text.config(state=tk.NORMAL),
                self.status_text.insert(tk.END, message + "\n"),
                self.status_text.see(tk.END),
                self.status_text.config(state=tk.DISABLED)
            ]
        )
    
    def show_summary(self):
        # 显示处理结果汇总
        summary = "处理完成！\n"
        summary += f"- 目标拼接时长：{self.stats['target_duration']}秒\n"
        summary += f"- 预处理：成功生成{self.stats['preprocessed_files']}个画布版视频，清理{self.stats['deleted_corrupt']}个损坏文件、{self.stats['deleted_empty']}个空文件、{self.stats['deleted_failed_preprocess']}个预处理失败文件\n"
        
        if self.stats['successfully_spliced'] > 0:
            summary += f"- 拼接结果：成功拼接{self.stats['successfully_spliced']}个视频（总时长分别为{', '.join([f'{d:.0f}秒' for d in self.stats['spliced_durations']])}），已移动至文件夹B\n"
        
        if self.stats['directly_moved'] > 0:
            summary += f"- 直接移动：{self.stats['directly_moved']}个视频（时长{', '.join([f'{d:.0f}秒' for d in self.stats['moved_durations']])}），已移动至文件夹B\n"
        
        if self.stats['deleted_source_files'] > 0:
            summary += f"- 原视频处理：已删除{self.stats['deleted_source_files']}个参与拼接的原视频（因勾选\"拼接后删除\"）\n"
        
        if self.stats['retained_files'] > 0:
            summary += f"- 保留文件：{self.stats['retained_files']}个视频，保留在文件夹A\n"
        
        self.root.after(0, lambda: messagebox.showinfo("处理结果", summary))
    
    def finish_processing(self):
        # 完成处理，恢复UI状态
        self.is_processing = False
        self.start_button.config(state=tk.NORMAL)
        self.update_progress("就绪")
    
    def cleanup_temp_files(self):
        # 清理临时文件
        cleaned_files_count = 0
        cleaned_dirs_count = 0
        
        # 清理当前临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # 统计目录中的文件数量
                dir_count = 0
                file_count = 0
                for root, dirs, files in os.walk(self.temp_dir):
                    dir_count += len(dirs)
                    file_count += len(files)
                
                shutil.rmtree(self.temp_dir)
                cleaned_dirs_count += 1
                cleaned_files_count += file_count
                logger.info(f"已清理临时目录: {self.temp_dir} (包含{file_count}个文件, {dir_count}个子目录)")
                self.append_status(f"已清理临时目录: {os.path.basename(self.temp_dir)}")
            except Exception as e:
                logger.error(f"清理临时目录失败: {str(e)}")
        
        # 清理系统临时目录中的相关文件
        try:
            for temp_dir in [tempfile.gettempdir()]:
                if os.path.exists(temp_dir):
                    temp_file_count = 0
                    temp_dir_count = 0
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        if "_画布版" in item or "moviepy" in item.lower():
                            try:
                                if os.path.isfile(item_path):
                                    os.remove(item_path)
                                    temp_file_count += 1
                                elif os.path.isdir(item_path):
                                    dir_files_count = 0
                                    for _, _, files in os.walk(item_path):
                                        dir_files_count += len(files)
                                    shutil.rmtree(item_path)
                                    temp_dir_count += 1
                                    temp_file_count += dir_files_count
                            except Exception as e:
                                logger.warning(f"清理临时文件失败: {item_path} ({str(e)})")
                    
                    if temp_file_count > 0 or temp_dir_count > 0:
                        cleaned_files_count += temp_file_count
                        cleaned_dirs_count += temp_dir_count
                        logger.info(f"已清理系统临时文件: {temp_file_count}个文件, {temp_dir_count}个目录")
        except Exception as e:
            logger.error(f"清理系统临时文件失败: {str(e)}")
        
        # 如果清理了文件或目录，添加状态信息
        if cleaned_files_count > 0 or cleaned_dirs_count > 0:
            self.append_status(f"已清理{cleaned_files_count}个临时文件和{cleaned_dirs_count}个临时目录")

if __name__ == "__main__":
    # 先检查moviepy库是否导入成功
    if not HAS_MOVIEPY:
        # 如果导入失败，显示错误信息并退出
        import sys
        print("错误: 无法导入moviepy库。请使用pip install moviepy命令安装。")
        sys.exit(1)
    
    # 如果导入成功，再创建GUI
    root = tk.Tk()
    app = VideoSplitterApp(root)
    
    # 捕获窗口关闭事件
    def on_closing():
        if app.is_processing:
            if messagebox.askyesno("提示", "处理正在进行中，确定要关闭窗口吗？"):
                app.stop_processing()
                root.destroy()
        else:
            app.cleanup_temp_files()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
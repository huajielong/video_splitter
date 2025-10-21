import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime
import tempfile
import threading
import logging
import warnings
from collections import Counter
import concurrent.futures
import multiprocessing
import time
import subprocess

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入PyAV库
HAS_PYAV = False
try:
    import av
    logger.info(f"PyAV版本: {av.__version__}")
    HAS_PYAV = True
    logger.info("成功导入PyAV库")
except ImportError as e:
    logger.error(f"无法导入PyAV库: {str(e)}")
    try:
        # 显示更详细的错误信息
        import sys
        print(f"错误详情: {str(e)}")
        print(f"Python版本: {sys.version}")
        print(f"当前目录: {os.getcwd()}")
    except:
        pass

# 设置PyAV环境
def setup_pyav_environment():
    # 定义一个简单的日志函数，防止logger未定义的情况
    def log_message(level, message):
        try:
            # 尝试使用全局logger
            if level == 'info':
                logger.info(message)
            elif level == 'warning':
                logger.warning(message)
            elif level == 'error':
                logger.error(message)
        except NameError:
            # 如果logger未定义，使用print
            print(f"[{level.upper()}] {message}")
    
    # 检查ffmpeg是否可用（PyAV通常会使用系统安装的ffmpeg）
    try:
        # 尝试运行ffmpeg命令来验证它是否可用，添加creationflags参数隐藏终端窗口
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=False, 
                      creationflags=subprocess.CREATE_NO_WINDOW)
        log_message('info', "系统中ffmpeg已可用")
    except (FileNotFoundError, Exception) as e:
        log_message('warning', f"可能无法访问ffmpeg: {str(e)}")

# 初始化PyAV环境
setup_pyav_environment()

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
        
        # 记录开始处理的时间
        self.processing_start_time = time.time()
        
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
            # 直接调用finish_processing恢复UI状态，而不是通过after延迟
            self.root.after(0, lambda: self._safe_finish_processing())
    
    def _preprocess_single_video(self, filename):
        """预处理单个视频，用于并行处理，添加视频属性检查优化"""
        result = {}
        file_path = os.path.join(self.folder_a.get(), filename)
        
        try:
            # 使用PyAV检查视频是否损坏并获取视频属性
            container = av.open(file_path)
            
            # 获取视频时长
            duration = container.duration / av.time_base  # 转换为秒
            
            # 获取视频流信息
            video_stream = None
            width, height = 0, 0
            for stream in container.streams:
                if stream.type == 'video':
                    video_stream = stream
                    width = stream.width
                    height = stream.height
                    break
            
            container.close()
            
            # 检查时长是否为0
            if duration <= 0:
                result['status'] = 'deleted_empty'
                result['filename'] = filename
                return result
            
            # 优化策略：检查视频是否已经是9:16比例且满足条件，无需预处理
            # 如果视频已经是竖屏且比例接近9:16（误差允许10%），可以直接使用原视频
            if height > width and abs((width/height) - (9/16)) < 0.1:
                self.append_status(f"视频已满足竖屏9:16比例，跳过预处理: {filename}")
                result['status'] = 'success'
                result['canvas_file'] = file_path  # 直接使用原文件
                result['orig_path'] = file_path
                result['duration'] = duration
                result['filename'] = filename
                result['width'] = width
                result['height'] = height
                return result
            
            # 预处理：生成9:16黑色画布+画中画
            canvas_file = self.create_canvas_video(file_path, filename, duration)
            if canvas_file:
                result['status'] = 'success'
                result['canvas_file'] = canvas_file
                result['orig_path'] = file_path
                result['duration'] = duration
                result['filename'] = filename
                # 保存尺寸信息
                try:
                    # 尝试快速获取生成视频的尺寸
                    probe_cmd = [
                        'ffprobe', '-v', 'error', 
                        '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height',
                        '-of', 'csv=p=0',
                        canvas_file
                    ]
                    probe_result = subprocess.run(probe_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                creationflags=subprocess.CREATE_NO_WINDOW)
                    dimensions = probe_result.stdout.decode().strip().split(',')
                    result['width'] = int(dimensions[0])
                    result['height'] = int(dimensions[1])
                except:
                    # 如果获取失败，使用画布默认尺寸
                    result['width'] = 1080
                    result['height'] = 1920
            else:
                result['status'] = 'deleted_failed_preprocess'
                result['filename'] = filename
                    
        except Exception as e:
            result['status'] = 'deleted_corrupt'
            result['filename'] = filename
            result['error'] = str(e)
            
        return result
    
    def preprocess_videos(self):
        """预处理视频，支持并行处理，按视频属性分组优化"""
        mp4_files = [f for f in os.listdir(self.folder_a.get()) if f.lower().endswith('.mp4')]
        canvas_files = []
        total_files = len(mp4_files)
        
        # 统计变量
        processed_count = 0
        skipped_count = 0  # 新增：跳过预处理的文件计数
        
        # 使用线程池并行处理视频
        # 最大线程数不超过6个，同时考虑CPU核心数和文件数量
        cpu_count = multiprocessing.cpu_count()
        recommended_workers = min(cpu_count * 2, len(mp4_files))
        max_workers = min(recommended_workers, 6)  # 限制最大线程数为6
        self.append_status(f"开始并行预处理视频，使用{max_workers}个线程（最大限制为6个线程）")
        
        # 新增：按视频属性预分类，优先处理小文件
        # 先快速获取文件大小信息进行粗略排序
        files_with_size = []
        for f in mp4_files:
            try:
                file_path = os.path.join(self.folder_a.get(), f)
                file_size = os.path.getsize(file_path)
                files_with_size.append((f, file_size))
            except:
                files_with_size.append((f, float('inf')))  # 无法获取大小的文件放最后
        
        # 按文件大小升序排序，优先处理小文件
        files_with_size.sort(key=lambda x: x[1])
        optimized_files = [f[0] for f in files_with_size]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_video = {executor.submit(self._preprocess_single_video, filename): filename for filename in optimized_files}
            
            # 处理完成的任务
            for future in concurrent.futures.as_completed(future_to_video):
                if not self.is_processing:
                    # 取消所有剩余任务
                    for f in future_to_video:
                        if not f.done():
                            f.cancel()
                    break
                
                processed_count += 1
                self.update_progress(f"正在预处理视频 ({processed_count}/{total_files})")
                
                try:
                    result = future.result()
                    filename = result['filename']
                    
                    # 根据处理结果更新统计和状态
                    if result['status'] == 'success':
                        # 检查是否是跳过预处理的文件
                        if result.get('canvas_file') == os.path.join(self.folder_a.get(), filename):
                            skipped_count += 1
                            # 添加视频尺寸信息到返回结果中，供后续排序使用
                            canvas_files.append((result['canvas_file'], result['orig_path'], result['duration'], 
                                               result.get('width', 0), result.get('height', 0)))
                        else:
                            self.append_status(f"预处理成功: {filename}")
                            # 添加视频尺寸信息到返回结果中，供后续排序使用
                            canvas_files.append((result['canvas_file'], result['orig_path'], result['duration'], 
                                               result.get('width', 0), result.get('height', 0)))
                        self.stats['preprocessed_files'] += 1
                    elif result['status'] == 'deleted_empty':
                        self.append_status(f"文件时长为0，删除: {filename}")
                        try:
                            os.remove(os.path.join(self.folder_a.get(), filename))
                            self.stats['deleted_empty'] += 1
                        except:
                            pass
                    elif result['status'] == 'deleted_failed_preprocess':
                        self.append_status(f"预处理失败，删除: {filename}")
                        try:
                            os.remove(os.path.join(self.folder_a.get(), filename))
                            self.stats['deleted_failed_preprocess'] += 1
                        except:
                            pass
                    elif result['status'] == 'deleted_corrupt':
                        error_msg = result.get('error', '未知错误')
                        self.append_status(f"文件损坏，删除: {filename} ({error_msg})")
                        try:
                            os.remove(os.path.join(self.folder_a.get(), filename))
                            self.stats['deleted_corrupt'] += 1
                        except:
                            pass
                except Exception as e:
                    filename = future_to_video[future]
                    self.append_status(f"处理视频时发生异常: {filename} ({str(e)})")
        
        # 记录优化统计
        if skipped_count > 0:
            self.append_status(f"优化处理：跳过预处理{skipped_count}个已满足条件的视频文件")
            self.stats['skipped_preprocess'] = skipped_count
        
        # 检查是否有预处理失败的视频
        if self.stats['deleted_failed_preprocess'] > 0:
            self.root.after(0, lambda: messagebox.showinfo("提示", 
                          f"检测到{self.stats['deleted_failed_preprocess']}个视频无法生成画布版，已自动删除"))
        
        return canvas_files
    
    def create_canvas_video(self, video_path, filename, duration):
        try:
            # 画布尺寸：1080x1920（9:16）
            canvas_width, canvas_height = 1080, 1920
            
            # 使用PyAV获取原视频尺寸
            container = av.open(video_path)
            stream = next((s for s in container.streams if s.type == 'video'), None)
            if not stream:
                raise ValueError("找不到视频流")
            
            # 获取视频尺寸
            orig_width = stream.width
            orig_height = stream.height
            container.close()
            
            # 计算调整后的尺寸（保持原比例）
            ratio = min(canvas_width / orig_width, canvas_height / orig_height)
            new_width = int(orig_width * ratio)
            new_height = int(orig_height * ratio)
            
            # 计算居中位置
            x_pos = (canvas_width - new_width) // 2
            y_pos = (canvas_height - new_height) // 2
            
            # 输出文件名 - 不再添加"画布版"后缀
            base_name = os.path.splitext(filename)[0]
            safe_name = self.filter_filename(base_name)
            output_path = os.path.join(self.temp_dir, f"{safe_name}.mp4")
            
            # 使用ffmpeg命令行工具来创建9:16画布并将原视频居中放置
            # 优化FFmpeg参数，使用更快的编码预设
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-threads', '0',  # 0表示使用所有可用线程
                '-i', video_path,
                '-f', 'lavfi', '-i', f'color=c=black:s={canvas_width}x{canvas_height}:d={duration}',
                '-filter_complex', f'[0:v]scale={new_width}:{new_height}[v1];[1:v][v1]overlay={x_pos}:{y_pos}[v]',
                '-map', '[v]', '-map', '0:a',
                '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast',  # 降低质量参数，提高速度
                '-c:a', 'aac', '-b:a', '64k',  # 更低的音频比特率以提高速度
                '-shortest', '-movflags', '+faststart',  # 启用快速启动
                '-vsync', '2',  # 使用帧丢弃模式，避免不必要的帧复制
                output_path
            ]
            
            # 执行ffmpeg命令，添加creationflags参数隐藏终端窗口
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                          creationflags=subprocess.CREATE_NO_WINDOW)
            
            return output_path
        except Exception as e:
            logger.error(f"创建画布视频失败: {str(e)}")
            return None
    
    def sort_videos(self, canvas_files):
        # 提取文件名和原路径
        file_info = []
        
        for item in canvas_files:
            # 处理包含5个元素的元组 (canvas_file, orig_path, duration, width, height)
            if len(item) >= 3:
                canvas_file = item[0]
                orig_path = item[1]
                duration = item[2]
                
                # 从元组中获取width和height，如果没有则后续通过PyAV获取
                width = item[3] if len(item) > 3 else 0
                height = item[4] if len(item) > 4 else 0
            else:
                # 兼容旧格式
                canvas_file, orig_path, duration = item
                width, height = 0, 0
                
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
            
            # 如果没有从元组中获取到尺寸信息，则使用PyAV获取
            if width == 0 or height == 0:
                try:
                    container = av.open(canvas_file)
                    stream = next((s for s in container.streams if s.type == 'video'), None)
                    if stream:
                        width = stream.width
                        height = stream.height
                    container.close()
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
                    self.append_status(f"开始拼接视频序列...")
                    
                    try:
                        # 获取视频路径列表
                        clip_paths = [canvas_file_seq for canvas_file_seq, _, _, _, _, _ in current_sequence]
                        
                        # 在开始写入前再次检查终止标志
                        if not self.is_processing:
                            self.append_status("处理已终止，取消视频拼接")
                            break
                        
                        # 构建输出文件名
                        base_names = [os.path.splitext(os.path.basename(f[0]))[0] for f in current_sequence]
                        safe_name = self.filter_filename("+".join(base_names))
                        output_path = os.path.join(self.folder_b.get(), f"{safe_name}.mp4")
                        
                        # 记录帧处理开始时间
                        frame_processing_start = time.time()
                        
                        # 使用FFmpeg进行视频拼接
                        # 1. 创建输入文件列表
                        input_list_path = os.path.join(self.temp_dir, "input_list.txt")
                        with open(input_list_path, 'w', encoding='utf-8') as f:
                            for path in clip_paths:
                                # 使用绝对路径并正确转义
                                escaped_path = path.replace('\\', '\\\\')
                                f.write(f"file '{escaped_path}'\n")
                        
                        # 2. 执行FFmpeg拼接命令
                        ffmpeg_cmd = [
                            'ffmpeg', '-y', '-threads', '0',
                            '-safe', '0', '-f', 'concat', '-i', input_list_path,
                            '-c:v', 'libx264', '-crf', '25', '-preset', 'ultrafast',
                            '-c:a', 'aac', '-b:a', '96k',
                            '-movflags', '+faststart',
                            output_path
                        ]
                        
                        # 执行命令
                        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                          creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        # 记录帧处理结束时间
                        frame_processing_time = time.time() - frame_processing_start
                        minutes, seconds = divmod(frame_processing_time, 60)
                        self.append_status(f"帧处理耗时：{int(minutes)}分{seconds:.1f}秒")
                        # 保存到统计信息中
                        if 'frame_processing_times' not in self.stats:
                            self.stats['frame_processing_times'] = []
                        self.stats['frame_processing_times'].append(frame_processing_time)
                        
                        # 记录统计信息
                        self.stats['successfully_spliced'] += 1
                        # 计算总时长（包含视频时长和帧处理时长）
                        total_duration = current_duration + frame_processing_time
                        # 保存总时长到统计信息
                        self.stats['spliced_durations'].append(total_duration)
                        self.append_status(f"视频序列拼接完成（总时长：{total_duration:.1f}秒，其中视频内容时长{current_duration:.1f}秒，帧处理耗时{frame_processing_time:.1f}秒）")
                        
                        # 如果需要删除源文件
                        if self.delete_source.get():
                            for _, orig_path_seq, _, _, _, _ in current_sequence:
                                source_files_to_delete.add(orig_path_seq)
                        
                    except Exception as e:
                        self.append_status(f"拼接视频时出错: {str(e)}")
                        logger.error(f"拼接视频时出错: {str(e)}")
                    finally:
                        # 清理输入文件列表
                        try:
                            input_list_path = os.path.join(self.temp_dir, "input_list.txt")
                            if os.path.exists(input_list_path):
                                os.remove(input_list_path)
                        except:
                            pass
        
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
        try:
            summary = "处理完成！\n"
            # 添加总耗时统计
            if hasattr(self, 'processing_start_time'):
                total_processing_time = time.time() - self.processing_start_time
                minutes, seconds = divmod(total_processing_time, 60)
                summary += f"- 总处理耗时：{int(minutes)}分{seconds:.1f}秒\n"
            summary += f"- 目标拼接时长：{self.stats['target_duration']}秒\n"
            # 新增：添加优化处理统计信息
            if 'skipped_preprocess' in self.stats and self.stats['skipped_preprocess'] > 0:
                skipped = self.stats['skipped_preprocess']
                summary += f"- 预处理：成功生成{self.stats['preprocessed_files'] - skipped}个画布版视频，优化跳过{skipped}个已满足条件的视频\n"
                summary += f"- 清理：{self.stats['deleted_corrupt']}个损坏文件、{self.stats['deleted_empty']}个空文件、{self.stats['deleted_failed_preprocess']}个预处理失败文件\n"
            else:
                summary += f"- 预处理：成功生成{self.stats['preprocessed_files']}个画布版视频\n"
                summary += f"- 清理：{self.stats['deleted_corrupt']}个损坏文件、{self.stats['deleted_empty']}个空文件、{self.stats['deleted_failed_preprocess']}个预处理失败文件\n"
            
            # 添加帧处理时间统计
            if 'frame_processing_times' in self.stats and self.stats['frame_processing_times']:
                total_frame_time = sum(self.stats['frame_processing_times'])
                minutes, seconds = divmod(total_frame_time, 60)
                summary += f"- 帧处理耗时：{int(minutes)}分{seconds:.1f}秒\n"
            
            if self.stats['successfully_spliced'] > 0:
                # 计算所有拼接视频的时长
                all_spliced_total_duration = sum(self.stats['spliced_durations'])
                minutes, seconds = divmod(all_spliced_total_duration, 60)
                summary += f"- 拼接结果：成功拼接{self.stats['successfully_spliced']}个视频\n"
                summary += f"- 所有拼接视频时长：{int(minutes)}分{seconds:.1f}秒\n"
            
            if self.stats['directly_moved'] > 0:
                # 计算所有直接移动视频的时长
                all_moved_total_duration = sum(self.stats['moved_durations'])
                minutes, seconds = divmod(all_moved_total_duration, 60)
                summary += f"- 直接移动：{self.stats['directly_moved']}个视频\n"
                summary += f"- 所有直接移动视频时长：{int(minutes)}分{seconds:.1f}秒\n"
            
            if self.stats['deleted_source_files'] > 0:
                summary += f"- 原视频处理：已删除{self.stats['deleted_source_files']}个参与拼接的原视频（因勾选\"拼接后删除\"）\n"
            
            if self.stats['retained_files'] > 0:
                summary += f"- 保留文件：{self.stats['retained_files']}个视频，保留在文件夹A\n"
            
            self.root.after(0, lambda: messagebox.showinfo("处理结果", summary))
        except Exception as e:
            logging.error(f"显示汇总信息时出错: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"显示处理结果时出错: {str(e)}"))
    
    def _safe_finish_processing(self):
        """安全地完成处理并恢复UI状态"""
        try:
            self.finish_processing()
        except Exception as e:
            # 捕获可能的异常，确保按钮状态总能恢复
            logger.error(f"恢复UI状态时出错: {str(e)}")
            try:
                # 直接尝试恢复按钮状态
                if hasattr(self, 'start_button') and hasattr(self, 'root'):
                    self.is_processing = False
                    self.start_button.config(state=tk.NORMAL)
                    self.update_progress("就绪")
            except:
                pass
    
    def finish_processing(self):
        # 计算处理总耗时
        if hasattr(self, 'processing_start_time'):
            total_processing_time = time.time() - self.processing_start_time
            self.stats['total_processing_time'] = total_processing_time
        
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
    # 先检查PyAV库是否导入成功
    if not HAS_PYAV:
        # 如果导入失败，显示错误信息并退出
        import sys
        print("错误: 无法导入PyAV库。请使用pip install av命令安装。")
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
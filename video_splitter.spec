# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 导入必要的模块
import os
import sys
import shutil

# 创建一个Analysis对象，指定要分析的脚本和依赖项
a = Analysis(['video_splitter.py'],
             pathex=['d:\python\pingjie'],
             binaries=[],
             datas=[],
              
             # 更新为PyAV相关的hiddenimports
             hiddenimports=[
                 'av',
                 'av.codec',
                 'av.codec.context',
                 'av.format',
                 'av.container',
                 'av.video',
                 'av.audio',
                 'subprocess',
                 'tkinter',
                 '_tkinter',
                 'tkinter.ttk',
                 'tkinter.filedialog',
                 'tkinter.font',
                 'tkinter.messagebox',
                 'tkinter.constants',
                 'concurrent.futures',
                 'multiprocessing',
                 'multiprocessing.shared_memory',
                 'numpy',
                 'PIL',
                 'PIL._tkinter_finder',
                 'tqdm',
                 'pkg_resources',
                 'importlib',
                 'importlib.resources'
             ],
             hookspath=[],
             runtime_hooks=[],
             # 增加更多的排除项以减小体积，但保留tkinter相关模块
             excludes=[
                 'matplotlib',
                 'jupyter',
                 'spyder',
                 'ipython',
                 'notebook',
                 'scipy',
                 'test',
                 'tests',
                 'doc',
                 'docs',
                 'numpy.testing',
                 'numpy.distutils',
                 'numpy.f2py',
                 'PIL.tests',
                 'PIL.ImageQt',
                 'PIL.ImageCms',
                 'PIL.ImageTransform',
                 'lib2to3',
                 'unittest',
                 'pytest',
                 'setuptools',
                 'wheel',
                 'pip',
                 'sqlite3',
                 'psutil',
                 'pygments',
                 'sphinx',
                 'docutils',
                 'chardet'
             ],
             cipher=block_cipher,
             # 使用archive模式减小体积
             noarchive=False)

# 优化DLL处理，只包含必要的DLL文件
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break

# 针对多版本Windows兼容性的最小DLL集
binaries_to_include = []
import os
import sys

# 查找系统DLL目录
system32_dir = os.path.join(os.environ['WINDIR'], 'System32')

# 只包含Windows 7必须的核心DLL文件
dll_list = [
    'VCRUNTIME140.dll',  # Visual C++运行时
    'MSVCP140.dll',      # Visual C++运行时
    'api-ms-win-crt-runtime-l1-1-0.dll',  # Windows通用运行时
    'api-ms-win-crt-stdio-l1-1-0.dll',
    'api-ms-win-crt-math-l1-1-0.dll',
    'api-ms-win-crt-time-l1-1-0.dll'
]

for dll in dll_list:
    dll_path = os.path.join(system32_dir, dll)
    if os.path.exists(dll_path):
        binaries_to_include.append((dll, dll_path, 'BINARY'))

# 添加Python核心DLL
python_dll_dir = os.path.dirname(sys.executable)
python_dll_list = ['python3.dll', 'python310.dll']
for dll in python_dll_list:
    dll_path = os.path.join(python_dll_dir, dll)
    if os.path.exists(dll_path):
        binaries_to_include.append((dll, dll_path, 'BINARY'))

# 添加PyAV相关的DLL
if hasattr(sys, 'base_prefix'):
    lib_dir = os.path.join(sys.base_prefix, 'Library', 'bin')
    av_dll_list = ['avcodec-58.dll', 'avformat-58.dll', 'avutil-56.dll', 'swresample-3.dll', 'swscale-5.dll']
    for dll in av_dll_list:
        dll_path = os.path.join(lib_dir, dll)
        if os.path.exists(dll_path):
            binaries_to_include.append((dll, dll_path, 'BINARY'))

# 添加所有找到的DLL到binaries
for dll_tuple in binaries_to_include:
    a.binaries.append(dll_tuple)

# 清理不必要的DLL，减小体积，但保留tkinter必需的tcl和tk相关DLL
unnecessary_dlls = ['QT5', 'wx', 'PySide', 'PyQt']
filtered_binaries = []
for binary in a.binaries:
    # 保留tcl和tk相关DLL，它们是tkinter所必需的
    if not any(unnecessary in binary[0] for unnecessary in unnecessary_dlls):
        filtered_binaries.append(binary)
a.binaries = filtered_binaries

# 确保包含tcl和tk相关DLL
try:
    import tkinter
    import os
    tcl_dir = os.path.dirname(tkinter.__file__)
    tcl_lib_dir = os.path.join(tcl_dir, 'tcl8.6')
    tk_lib_dir = os.path.join(tcl_dir, 'tk8.6')
    
    # 添加tcl库
    if os.path.exists(tcl_lib_dir):
        a.datas.extend([(os.path.join('tcl8.6', f), os.path.join(tcl_lib_dir, f), 'DATA') for f in os.listdir(tcl_lib_dir) if os.path.isfile(os.path.join(tcl_lib_dir, f))])
    
    # 添加tk库
    if os.path.exists(tk_lib_dir):
        a.datas.extend([(os.path.join('tk8.6', f), os.path.join(tk_lib_dir, f), 'DATA') for f in os.listdir(tk_lib_dir) if os.path.isfile(os.path.join(tk_lib_dir, f))])
except Exception as e:
    pass  # 如果无法找到tcl/tk库，继续打包

# 创建一个PYZ对象，包含Python字节码
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建EXE对象，配置为Windows上的可执行文件
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='视频自动拼接与移动工具_修复版',  # 使用新名称避免文件锁定问题
          debug=False,
          strip=True,
          upx=True,
          upx_exclude=['VCRUNTIME140.dll', 'MSVCP140.dll', 'api-ms-win-crt-*.dll', 'python3.dll', 'python310.dll'],
          runtime_tmpdir=None,
          console=False,  # 确保不显示控制台窗口
          disable_windowed_traceback=True,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          optimize=2,
          icon=None)
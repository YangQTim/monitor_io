import subprocess
import time
import threading
from tkinter import *
from tkinter import ttk
import queue
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math
import logging

log_queue = queue.Queue()

def log_message(message):
    """将日志消息插入到 Text 组件中"""
    log_queue.put(message)  # 将日志消息放入队列中
    logging.info(message)

def process_log_queue():
    """处理日志队列中的消息，并插入到 Text 组件中"""
    while not log_queue.empty():
        message = log_queue.get_nowait()
        if log_text:
            log_text.insert(END, message + '\n')
            log_text.yview(END)
    root.after(100, process_log_queue)  # 每100ms检查一次队列

def send_command(proc, command, wait=1):
    """发送命令到子进程，并等待指定时间"""
    print(f"发送命令: {command}")
    proc.stdin.write(command + "\n")
    proc.stdin.flush()
    time.sleep(wait)

def show_current_focus_window():
    """打印当前active window"""
    activity = get_current_focus_window()
    if activity:
        log_message(f"Activity:{activity}")
    else:
        log_message("Fail to query current activity.")

def clear_text(text):
    text.delete('1.0', END)

def get_app_startup_time(name):
    """Calculate the startup time of the application"""
    result = subprocess.run(["adb", "shell", f"am start -S -W {name}"], capture_output=True, text=True)
    if result.returncode != 0:
        log_message("Failed to query application startup time")
        return None

    '''
    ThisTime
    最后一个Activity启动耗时,如果关心应用有界面Activity启动耗时,参考ThisTime

    TotalTime
    所有Activity启动耗时,一般查看得到的TotalTime,即应用的启动时间.
    包括创建进程 + Application初始化 + Activity初始化到界面显示的过程。如果只关心某个应用自身启动耗时,参考TotalTime

    WaitTime
    AMS启动Activity的总耗时,如果关心系统启动应用耗时,参考WaitTime
    '''
    totalTime = None
    waitTime = None
    for line in result.stdout.splitlines():
        if "TotalTime" in line or "WaitTime" in line:
            parts = line.split()
            if "TotalTime" in line and len(parts) > 1:
                totalTime = parts[1]
            else:
                waitTime = parts[1]
        if totalTime and waitTime:
            log_message(f"Application total startup time: TotalTime is {totalTime} ms, WaitTime is {waitTime} ms")
            break

    return None

def plot_canvas(root):
    global fps_plot, io_plot, cpu_plot, gpu_plot, canvas
    f = Figure(figsize=(6, 3), dpi=100)#figsize定义图像大小，dpi定义像素

    # 在创建子图fps_plot变量
    fps_plot = f.add_subplot(411)
    fps_plot.clear()
    fps_plot.set_ylabel('Values')
    fps_plot.set_title('FPS Performance Metrics')
    fps_plot.set_xlim(0, 30)
    fps_plot.set_ylim(0, 70)

    # 在创建子图io_plot变量
    io_plot = f.add_subplot(412)
    io_plot.clear()
    io_plot.set_ylabel('Values')
    io_plot.set_title('IO Performance Metrics')
    io_plot.set_xlim(0, 30)
    io_plot.set_ylim(0, 20)

    # 在创建子图cpu_plot变量
    cpu_plot = f.add_subplot(413)
    cpu_plot.clear()
    cpu_plot.set_ylabel('Values')
    cpu_plot.set_title('CPU Performance Metrics')
    cpu_plot.set_xlim(0, 30)
    cpu_plot.set_ylim(0, 30)

    # 在创建子图gpu_plot变量
    gpu_plot = f.add_subplot(414)
    gpu_plot.clear()
    gpu_plot.set_ylabel('Values')
    gpu_plot.set_title('GPU Performance Metrics')
    gpu_plot.set_xlim(0, 30)
    gpu_plot.set_ylim(-500, 500)
    
    f.subplots_adjust(top=0.9,bottom=0.1,hspace=0.5)

    canvas = FigureCanvasTkAgg(f, root)#f是定义的图像，root是tkinter中画布的定义位置
    canvas.get_tk_widget().grid(row=0, column=4, rowspan=6,sticky=NSEW, padx=10, pady=10)
    canvas.draw()
    return canvas

def update_fps():
    global fps_x, fps_y, fps_plot
    fps_plot.clear()
    fps_x.append(fps_x[-1] + 1)
    fps_y.append(fps)
    if len(fps_x) > 30:
        fps_x.pop(0)
        fps_y.pop(0)
    fps_plot.plot(fps_x, fps_y)
    if max(fps_x) < 30:
        fps_plot.set_xlim(0, 30)
    fps_plot.set_ylim(0, 70)
    fps_plot.set_title('FPS Performance Metrics')
    fps_plot.text(fps_x[-1] - 1,fps_y[-1] + 5,'%.2f' % fps,fontdict={'fontsize':11})


def update_io_stats():
    global io_x, io_yR, io_yW, io_plot, io_yList
    io_plot.clear()
    io_x.append(io_x[-1] + 1)
    io_yR.append(read_bytes_sec)
    io_yW.append(write_bytes_sec)
    ###增加io_yList,记录当前30s窗口内最大y值,以30s窗口内最大y值确定Y轴范围
    io_yList.append(read_bytes_sec)
    io_yList.append(write_bytes_sec)
    if len(io_x) > 30:
        io_x.pop(0)
        io_yR.pop(0)
        io_yW.pop(0)
        ###yList是read_bytes_sec，write_bytes_sec的组合，需要删除两次
        io_yList.pop(0)
        io_yList.pop(0)
    io_plot.plot(io_x, io_yR)
    io_plot.plot(io_x, io_yW)
    io_plot.set_title('IO Performance Metrics')

    if max(io_x) < 30:
        io_plot.set_xlim(0, 30)
    if max(io_yList) > 2000:
        io_plot.set_ylim(0, 5000)
        label_position = 5000/10 + 0.5
    elif max(io_yList) > 1000:
        io_plot.set_ylim(0, 2000)
        label_position = 2000/10 + 0.5
    elif max(io_yList) > 500:
        io_plot.set_ylim(0, 1000)
        label_position = 1000/10 + 0.5
    elif max(io_yList) > 100:
        io_plot.set_ylim(0, 500)
        label_position = 500/10 + 0.5
    elif max(io_yList) > 50:
        io_plot.set_ylim(0, 100)
        label_position = 100/10 + 0.5
    elif max(io_yList) > 30:
        io_plot.set_ylim(0, 50)
        label_position = 50/10 + 0.5
    elif max(io_yList) > 20:
        io_plot.set_ylim(0, 30)
        label_position = 30/10 + 0.5
    elif max(io_yList) > 10:
        io_plot.set_ylim(0, 20)
        label_position = 20/10 + 0.5
    else:
        io_plot.set_ylim(0, 10)
        label_position = 10/10 + 0.5
    io_plot.text(io_x[-1] - 1,io_yR[-1] + 0.5 ,f'rb {read_bytes_sec:.2f} kB/s',fontdict={'fontsize':11})
    io_plot.text(io_x[-1] - 1,io_yW[-1] + label_position,f'wb {write_bytes_sec:.2f} kB/s',fontdict={'fontsize':11})


def update_cpu_stats():
    global cpu_x, cpu_y, cpu_plot
    cpu_plot.clear()
    cpu_x.append(cpu_x[-1] + 1)
    cpu_y.append(cpu_usage)
    if len(cpu_x) > 30:
        cpu_x.pop(0)
        cpu_y.pop(0)
    cpu_plot.plot(cpu_x, cpu_y)
    cpu_plot.set_title('CPU Performance Metrics')
    if max(cpu_x) < 30:
        cpu_plot.set_xlim(0, 30)
    if max(cpu_y) > 400:
        cpu_plot.set_ylim(0, 800)
    elif max(cpu_y) > 200:
        cpu_plot.set_ylim(0, 400)
    elif max(cpu_y) > 100:
        cpu_plot.set_ylim(0, 200)
    elif max(cpu_y) > 50:
        cpu_plot.set_ylim(0, 100)
    elif max(cpu_y) > 30:
        cpu_plot.set_ylim(0, 50)
    else:
        cpu_plot.set_ylim(0, 30)
    cpu_plot.text(cpu_x[-1] - 1,cpu_y[-1] + 5,f'{cpu_usage}%',fontdict={'fontsize':11})

def update_gpu_stats():
    global gpu_x, gpu_y, gpu_plot, gpu
    gpu_plot.clear()
    gpu_x.append(gpu_x[-1] + 1)
    gpu_y.append(gpu)
    if len(gpu_x) > 30:
        gpu_x.pop(0)
        gpu_y.pop(0)
    gpu_plot.plot(gpu_x, gpu_y)
    if max(gpu_x) < 30:
        gpu_plot.set_xlim(0, 30)
    if max(gpu_y) > 50:
        gpu_plot.set_ylim(0, 100)
        label_position = 100/10
    elif max(gpu_y) > 30:
        gpu_plot.set_ylim(0, 50)
        label_position = 50/10
    else:
        gpu_plot.set_ylim(0, 30)
        label_position = 30/10

    gpu_plot.set_title('GPU Performance Metrics')
    if len(gpu_x) < 7:
        gpu_plot.text(gpu_x[-1] - 1,gpu_y[-1] + label_position,f'{0.00} %',fontdict={'fontsize':11})
    else:
        gpu_plot.text(gpu_x[-1] - 1,gpu_y[-1] + label_position,f'{gpu:.1f} %',fontdict={'fontsize':11})

def update_metrics():
    global monitor, canvas
    if monitor:
        # 更新各个画布
        update_fps()
        update_io_stats()
        update_cpu_stats()
        update_gpu_stats()
        canvas.draw()
        # 每隔一段时间更新一次
        root.after(500, update_metrics)  # 每500ms更新一次
    else:
        root.after(100, update_metrics)

def find_indices(header_line):
    # """从标题行中找到IntendedVsync和FrameCompleted的索引"""
    headers = header_line.strip().split(',')
    intended_vsync_index = headers.index("IntendedVsync")
    frame_completed_index = headers.index("FrameCompleted")
    return intended_vsync_index, frame_completed_index
	
def get_pid(package_name):
    """Get the PID of the given package name."""
    result = subprocess.run(["adb", "shell", "pidof", package_name], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def get_io_stats(pid):
    """Get the IO statistics for the given PID."""
    result = subprocess.run(["adb", "shell", f"cat /proc/{pid}/io"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    io_stats = {}
    for line in result.stdout.splitlines():
        key, value = line.split(': ')
        io_stats[key.strip()] = int(value.strip())
    return io_stats

def get_foreground_window_name(package_name):
    """Get the foreground window name for the given package name."""
    result = subprocess.run(["adb", "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], capture_output=True, text=True)
    ###等效命令
    # result = subprocess.run(["adb", "shell", "dumpsys activity | grep mResume"], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    lines = result.stdout.splitlines()
    for line in lines:
        if package_name in line:
            parts = line.split()
            if len(parts) > 1:
                window_name = parts[-1][:-1]
                return window_name
    return None


def get_frame_stats(package_name,current_focus_window):
    """New function to get the frame statistics using gfxinfo."""
    global last_timestamp,fps
    intended_vsync_index = 0
    frame_completed_index = 0

    result = subprocess.run(["adb", "shell", f"dumpsys gfxinfo {package_name} framestats"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    lines = result.stdout.splitlines()
    timestamps = []
    each_frame_timestamps = []
    isHaveFoundWindow = False
    PROFILEDATA_line = 0

    for line in lines:
        ###调试一下
        if "Window" in line and current_focus_window in line:
            isHaveFoundWindow = True
            continue
        if isHaveFoundWindow and "---PROFILEDATA---" in line:
            PROFILEDATA_line += 1
            continue
        if isHaveFoundWindow and "IntendedVsync" in line:
            intended_vsync_index, frame_completed_index = find_indices(line)
            continue
        if isHaveFoundWindow and (PROFILEDATA_line == 1) and (intended_vsync_index & frame_completed_index) != 0:
            # 此处代表的是当前活动窗口
            fields = []
            fields = line.split(",")
            each_frame_timestamp = [float(fields[intended_vsync_index]), float(fields[frame_completed_index])]
            each_frame_timestamps.append(each_frame_timestamp)
            continue
        if PROFILEDATA_line >= 2:
            break
    
    # 需要在计算次数前去除重复帧，通过每帧的起始时间去判断是否是重复的
    for timestamp in each_frame_timestamps:
            if timestamp[0] > last_timestamp:
                timestamps.append((timestamp[1] - timestamp[0]) / 1000000)
                last_timestamp = timestamp[0]
    
    janky_list = []
    vsyncOverTimes = 0
    FER = 0.00
    janke_frames = ""
    ###界面没有刷新,维持上一次刷新的FPS
    if len(timestamps) == 0:
        pass
    else:
        frame_count = len(timestamps)
         # 统计丢帧和需要垂直同步次数
        for timestamp in timestamps:
            if timestamp > 16.67:
                # 超过16.67ms
                janky_list.append(timestamp)
                if timestamp % 16.67 == 0:
                    vsyncOverTimes += ((timestamp / 16.67) - 1)
                else:
                    vsyncOverTimes += math.floor(timestamp / 16.67)

        fps = frame_count / (frame_count + vsyncOverTimes) * 60
        FER = len(janky_list) / frame_count * 100

    janke_frames = f"Janky frames: {len(janky_list)} ({FER:.2f}%)"
    return fps,janke_frames

def get_meminfo(package_name):
    """Get the memory used info."""
    global last_meminfo_io
    try:
        result = subprocess.run(["adb", "shell", f"dumpsys meminfo {package_name}"], capture_output=True, text=True)
        if result.returncode!= 0:
            return None
        memory_usage = {}
        lines = result.stdout.splitlines()
        for line in lines:
            if "TOTAL PSS" in line:
                parts = line.split()
                memory_usage["TOTAL PSS"] = parts[2]
                memory_usage["TOTAL RSS"] = parts[5]
                memory_usage["meminfo_io"] = int(parts[2]) - last_meminfo_io
                last_meminfo_io = int(parts[2])
            elif "Views" in line and "WebViews" not in line:
                parts = line.split()
                memory_usage["Views"] = parts[1] 
            elif "Activities" in line:
                parts = line.split()
                memory_usage["Activities"] = parts[3]   
            else: 
                pass
        return memory_usage

    except Exception as e:
        log_message(f"An error occurred while getting memory information for {package_name}: {e}")
        return None


def get_current_focus_window():
    """Get the mLastPausedActivity info."""
    result = subprocess.run(["adb", "shell", "dumpsys window | grep 'mCurrentFocus'"], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    lines = result.stdout.splitlines()
    for line in lines:
        if "mCurrentFocus" in line:
            parts = line.split()
            if len(parts) > 1:
                activity = parts[-1][:-1]
                packageName = activity.split("/")[0]
                if "/." in activity:
                    activityName = packageName + "/" + packageName + "." + activity.split("/.")[1]
                else:
                    activityName = activity
                return activityName
    return None

def monitor_touch_events(event_type):
    global touchNum,touch_process
    # 使用ADB命令监控触摸事件
    command = ["adb", "shell", "getevent", "-lt",event_type]
    touch_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for line in iter(touch_process.stdout.readline, ''):
                if line and "SYN_REPORT" in line:
                    # 处理并输出触摸事件数据
                    # log_message("Touch Event: ", line.strip())
                    touchNum = touchNum + 1
    except KeyboardInterrupt:# 捕获Ctrl+C中断信号
        log_message("Stopping touch event monitor.")
    finally:
        touch_process.stdout.close()
        touch_process.stderr.close()
        touch_process.kill()
    
def monitor_cpu():
    global cpu_process, cpu_usage,pid
    # 使用CPU监控事件
    while True:
        if stop_threads:
            break
        if len(pid) > 0:
            result = subprocess.run(["adb", "shell", f"top -n 1 -p {pid}"], capture_output=True, text=True)
            if result.returncode != 0:
                cpu_usage = 0

            lines = result.stdout.strip().splitlines()
            cleaned_list = [item for item in lines if item]
            for i in range(len(cleaned_list)):
                if "TIME+ ARGS" in cleaned_list[i]:
                    line = re.compile(r'\x1b\[.*?m').sub('', cleaned_list[i+1])
                    cpu_usage = float(line.split()[8])

def monitor_gpu():
    global gpu_process,gpu
    login_commands = [
        "su",
        "busybox telnet 192.168.8.1",  # 替换为实际的QNX IP地址
        "dsv2022",  # 登录用户名
        "sv2970188",  # 登录密码
        "su root",  # 切换到root用户
        "Sv@2655888",  # root密码
    ]
    
    gpu_commands = [
        "echo gpu_set_log_level 0 > /dev/kgsl-control",
        "echo gpubusystats 0 > /dev/kgsl-control",
        "echo gpu_set_log_level 4 > /dev/kgsl-control",
        "echo gpubusystats 1000 > /dev/kgsl-control",
        "slog2info -W | grep -i kgsl"
    ]
    print("开始连接并登录QNX系统")    

    try:
        # 启动 adb shell
        gpu_process = subprocess.Popen(
            "adb shell", 
            shell=True, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            bufsize=1  # 行缓冲
        )

        # 执行登录命令
        for command in login_commands:
            send_command(gpu_process, command)
        print("成功登录QNX系统，开始设置和监控GPU信息")  
        
        # 设置GPU监控
        for command in gpu_commands:
            send_command(gpu_process, command, wait=1)
        print("成功设置和监控GPU信息")

        while True:
            if stop_threads:
                break
            output = gpu_process.stdout.readline()
            if output == '' and gpu_process.poll() is not None:
                break
            if output and "percentage busy" in output:
                part = output.strip().split()
                gpu = float(part[-1][:-1])
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 确保进程关闭
        gpu_process.terminate()
        gpu_process.wait()


def start_monitor_thread(package_name, event_type, interval=0.5):
    global monitor_thread
    """启动监控线程"""
    monitor_thread = threading.Thread(target=monitor_io_and_fps, name="IO_FPS_Thread", args=(package_name, interval))
    monitor_thread.daemon = True
    monitor_thread.start()


def start_monitor_touch_events_thread(event_type):
    global touch_thread
    """启动触摸事件监控线程"""
    touch_thread = threading.Thread(target=monitor_touch_events, name="touch_Thread", args=(event_type,))
    touch_thread.daemon = True
    touch_thread.start()

def start_monitor_cpu_thread():
    global cpu_thread
    """启动CPU TOP监控线程"""
    cpu_thread = threading.Thread(target=monitor_cpu, name="cpu_Thread")
    cpu_thread.daemon = True
    cpu_thread.start()

def start_monitor_gpu_thread():
    global gpu_thread
    """启动CPU TOP监控线程"""
    gpu_thread = threading.Thread(target=monitor_gpu, name="gpu_Thread")
    gpu_thread.daemon = True
    gpu_thread.start()

def start_to_Monitor(package_name, event_type, interval=0.5):
    global monitor,prev_timer,stop_threads,prev_meminfo_timer
    if not monitor:
        prev_timer = time.time()    ###记录IO初始时间
        prev_meminfo_timer = time.time()
        stop_threads = False
        start_monitor_thread(package_name,event_type,interval)
        start_monitor_touch_events_thread(event_type)
        start_monitor_cpu_thread()
        start_monitor_gpu_thread()
    else:
        log_message("Monitor is running")

def kill_thread():
    global monitor_thread, touch_thread, cpu_thread, gpu_thread, stop_threads, monitor, touch_process, pid
    stop_threads = True
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join()
    if touch_thread and touch_thread.is_alive():
        touch_process.kill()
        touch_thread.join()
    if cpu_thread and cpu_thread.is_alive():
        cpu_thread.join()
    if gpu_thread and gpu_thread.is_alive():
        gpu_thread.join()
    monitor = False
    pid = ""
    log_message("Monitoring stopped.")


def open_root():
    global root, log_text, chart_frame, canvas, pid

    root = Tk()
    root.title("Android Monitor")
    root.geometry("1550x950")

    # package name combobox
    label1 = Label(root, text="package name:")
    label1.grid(row=0, column=0, sticky=NW, padx=10, pady=10)

    box1 = ttk.Combobox(root, width=50)
    box1['values'] = ('com.gxatek.cockpit.car.settings', 'com.gxatek.cockpit.weather', 'syncore.space.cockpit.toplauncher')
    box1.current(0)
    box1.grid(row=0, column=1, sticky=NW, padx=10, pady=10)

    # getevent下拉框
    label2 = Label(root, text="event:")
    label2.grid(row=1, column=0, sticky=NW, padx=10, pady=10)

    box2 = ttk.Combobox(root, width=50)
    box2['values'] = ('/dev/input/event0', '/dev/input/event1', '/dev/input/event2', '/dev/input/event3', '/dev/input/event4', '/dev/input/event5')
    box2.current(0)
    box2.grid(row=1, column=1, sticky=NW, padx=10, pady=10)

    button = Button(root, text="开始监控", command=lambda: start_to_Monitor(box1.get(), box2.get(), interval=0.5), width=50)
    button.grid(row=0, column=2, sticky=NSEW, padx=10, pady=10)

    stop_button = Button(root, text="停止监控", command=kill_thread)
    stop_button.grid(row=4, column=2, sticky=NSEW, padx=10, pady=10)

# 查询启动时间下拉框
    label3 = Label(root, text="activity:")
    label3.grid(row=2, column=0, sticky=NW, padx=10, pady=10)

    box3 = ttk.Combobox(root, width=50)
    box3['values'] = ('com.gxatek.cockpit.car.settings/com.gxatek.cockpit.carsetting.view.activity.SettingActivity','com.autonavi.amapauto/com.autonavi.amapauto.MainMapActivity')
    # box3.current(0)
    box3.grid(row=2, column=1, sticky=NW, padx=10, pady=10)   

    query_button = Button(root, text="查询启动时间", command=lambda: get_app_startup_time(box3.get()))
    query_button.grid(row=1, column=2, sticky=NSEW, padx=10, pady=10)

    query_button2 = Button(root, text="查询Activity", command=lambda: show_current_focus_window())
    query_button2.grid(row=2, column=2, sticky=NSEW, padx=10, pady=10)


    # 创建日志文本框和滚动条
    label3 = Label(root, text="日志输出:")
    label3.grid(row=4, column=0, sticky=NW, padx=10, pady=10)

    log_frame = Frame(root)
    log_frame.grid(row=5, column=0, columnspan=3, sticky=NS, padx=10, pady=10)

    log_text = Text(log_frame)
    log_text.grid(row=0, column=0, columnspan=3,sticky=NS,ipadx=150,ipady=180)

    scrollbar = Scrollbar(log_frame, command=log_text.yview)
    scrollbar.grid(row=0, column=3, sticky=NS)
    log_text.config(yscrollcommand=scrollbar.set)

    clear_button = Button(root, text="清空日志", command=lambda: clear_text(log_text))
    clear_button.grid(row=3, column=2, sticky=NSEW, padx=10, pady=10)

    # 创建柱状图标签
    chart_frame = ttk.Frame(root)
    chart_frame.grid(row=0, column=3, rowspan=6, sticky=NS, padx=10, pady=10)

    canvas = None
    canvas = plot_canvas(root)
    update_metrics()    # 更新图表

    process_log_queue()  # 启动处理日志队列的定时器


    root.mainloop()

def monitor_io_and_fps(package_name,interval=0.5):
    global touchNum,monitor,chart_frame,pid
    global read_bytes_sec,write_bytes_sec,fps,cpu_usage ###绘图全局变量
    global prev_timer,prev_meminfo_timer,memory_io

    """Monitor the IO throughput and FPS of the given package name."""
    pid = get_pid(package_name)
    if not pid :
        log_message(f"Could not find PID for package: {package_name}")
        return

    window_name = get_foreground_window_name(package_name)
    if not window_name:
        log_message(f"Could not find foreground window for package: {package_name}")
        return

    ###yqt 重启后获取root权限
    getRoot = subprocess.run(["adb", "root"])
    if getRoot.returncode != 0:
        log_message(f"Could not get IO stats for PID: {pid}root")
        return 
	
    log_message(f"Monitoring IO and FPS for {package_name} (PID: {pid}, Window: {window_name})")
    prev_io_stats = get_io_stats(pid)
    if not prev_io_stats:
        log_message(f"Could not get IO stats for PID: {pid}")
        return

    while True:
        if stop_threads:
            break

        """clear"""
        cmd = "adb shell dumpsys gfxinfo {} reset".format(package_name)
        try:
            subprocess.check_output(cmd, shell=True).decode()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")

        monitor = True # 监控标志,防止多次点击监控
        time.sleep(interval)
        log_message(time.strftime('%H:%M:%S', time.localtime()))

        current_focus_window = get_current_focus_window()
        if not current_focus_window:
            log_message(f"Could not find the current focus window ")
        else:
            log_message(f"The current focus window: {current_focus_window}")

        current_io_stats = get_io_stats(pid)
        current_timer = time.time()
        if not current_io_stats:
            log_message(f"Could not get IO stats for PID: {pid}")
            return

        read_bytes_diff = current_io_stats.get("read_bytes", 0) - prev_io_stats.get("read_bytes", 0)
        write_bytes_diff = current_io_stats.get("write_bytes", 0) - prev_io_stats.get("write_bytes", 0)
        interval_time = (current_timer - prev_timer)
        read_bytes_sec = (read_bytes_diff / interval_time) / 1024
        write_bytes_sec = (write_bytes_diff / interval_time) / 1024
        prev_io_stats = current_io_stats
        prev_timer = current_timer
        log_message(f"Read: {read_bytes_sec:.1f} kBytes/s, Write: {write_bytes_sec:.1f} kBytes/s")
        
        ##内存
        meminfo = get_meminfo(package_name)# 读取内存使用情况,return类型为dict 
        current_meminfo_timer = time.time()
        interval_meminfo_time = (current_meminfo_timer - prev_meminfo_timer)
        prev_meminfo_timer = current_timer
        if not meminfo:
            log_message(f"No vaild Memory info")
        else:
            log_message(f"Memory Usage infomation\tTotal PSS:{(int(meminfo['TOTAL PSS'])/1024):.1f} MB,\t\tTotal RSS:{(int(meminfo['TOTAL RSS'])/1024):.1f} MB,\t\tViews:{meminfo['Views']},\t\tActivities:{meminfo['Activities']}")
            memory_io = (int(meminfo['meminfo_io'])/interval_meminfo_time)
            log_message(f"Memory Usage throughput {memory_io:.1f} KB/s")


        fps,janky_frames = get_frame_stats(package_name,current_focus_window)
        if fps is None:
            log_message(f"FPS: N/A,{janky_frames}")
        else:
            log_message(f"FPS: {fps:.2f},{janky_frames}")
        
        ###CPU
        log_message(f"{package_name} CPU usage:{cpu_usage:.1f}%")
        ###GPU
        if gpu == 0:
            log_message(f"Waiting for GPU info")
        else:
            log_message(f"GPU usage:{gpu:.2f}%")
        log_message(f"Monitor: {touchNum} CPS\n")
        touchNum = 0 # 重置touchNum

def set_logging():
    ### 日志
    logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为DEBUG，意味着会记录所有级别的日志
    format='%(asctime)s - %(levelname)s - %(message)s',  # 设置日志输出格式
    filename=rf'D:\Git-script\monitor_io\log\{current_time}.log',  # 设置日志文件名
    filemode='a'  # 追加模式（默认是'a'，即追加日志到文件末尾；'w'表示写模式，每次覆盖文件内容）
)

if __name__ == "__main__":
    global touchNum # 初始化touchNum
    touchNum = 0
    global monitor 
    monitor = False
    global pid
    pid = ""
    global read_bytes_sec
    global write_bytes_sec
    global fps
    global cpu_usage
    cpu_usage = read_bytes_sec = write_bytes_sec  = 0.00 # 初始化绘图全局变量
    fps = 60.0
    global gpu
    gpu = 0.00
    global stop_threads 
    stop_threads = False
    global monitor_thread 
    monitor_thread = None
    global touch_thread
    touch_thread = None
    global cpu_thread
    cpu_thread = None
    global gpu_thread
    gpu_thread = None
    current_time = time.strftime('%Y-%m-%d %H_%M_%S', time.localtime())
    global prev_timer
    prev_timer = None
    global last_timestamp
    last_timestamp = 0
    global prev_meminfo_timer
    prev_meminfo_timer = None
    global last_meminfo_io
    last_meminfo_io = 0
    global memory_io
    memory_io = 0
    global fps_x, fps_y, io_x, io_yR, io_yW, cpu_x, cpu_y, gpu_x, gpu_y

    fps_x, fps_y, io_x, io_yR, io_yW, cpu_x, cpu_y, gpu_x, gpu_y= [0], [0], [0], [0], [0], [0], [0], [0], [0]
    global io_yList
    io_yList = []

    set_logging()
    open_root()
                
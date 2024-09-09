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


def plot_io_stats(read_bytes_sec, write_bytes_sec):
    """绘制读写速率的柱状图"""
    plt.close("all")

    labels = ['read', 'write']
    values = [read_bytes_sec, write_bytes_sec]
    x = np.arange(len(labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(3, 2))
    bars = ax.bar(x, values, width)

    ax.set_ylabel('Values')
    ax.set_title('IO Performance Metrics')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    #ax.legend()

    def autolabel(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        height = []
        for rect in rects:
            current_height = rect.get_height()
            height.append(rect.get_height())
            ###(height*1.2)+1,防止ax.set_ylim最大值最小值均为0时的UserWarning
            ###height*1.2是为了增加y轴刻度范围，方便元素数值显示
            ###height_max图表有多列时，取数值最大者定义y轴刻度范围，方便元素数值显示
            height_max = max(height)
            ax.set_ylim(0, (height_max*1.2)+1)
            ax.annotate(f'{current_height:.1f} kb/s',
                        xy=(rect.get_x() + rect.get_width() / 2, current_height),
                        xytext=(0, 2),  # 2 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    autolabel(bars)
    plt.tight_layout()

    return fig

def plot_fps(fps):
    """绘制FPS的柱状图"""
    plt.close("all")

    labels = ['fps']
    values = [fps]

    x = np.arange(len(labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(3, 2))
    bars = ax.bar(x, values, width)

    ax.set_ylabel('Values')
    ax.set_title('FPS Performance Metrics')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    #ax.legend()

    def autolabel(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        for rect in rects:
            height = rect.get_height()
            ###(height*1.2)+1,防止ax.set_ylim最大值最小值均为0时的UserWarning
            ###height*1.2是为了增加y轴刻度范围，方便元素数值显示
            # ax.set_ylim(0, (height*1.2)+1)
            ax.set_ylim(0,70)
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2),  # 2 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    autolabel(bars)

    plt.tight_layout()

    return fig

def plot_cpu_stats(package_cpu_usage, total_cpu_usage):
    """绘制CPU使用率的柱状图"""
    plt.close("all")

    labels = ['package_cpu_usage', 'total_cpu_usage']
    values = [package_cpu_usage, total_cpu_usage]

    x = np.arange(len(labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(3, 2))
    bars = ax.bar(x, values, width)

    ax.set_ylabel('Values')
    ax.set_title('CPU Performance Metrics')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    #ax.legend()
    def autolabel(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        height = []
        for rect in rects:
            current_height = rect.get_height()
            height.append(rect.get_height())
            ###(height*1.2)+1,防止ax.set_ylim最大值最小值均为0时的UserWarning
            ###height*1.2是为了增加y轴刻度范围，方便元素数值显示
            ###height_max图表有多列时，取数值最大者定义y轴刻度范围，方便元素数值显示
            height_max = max(height)
            ax.set_ylim(0, (height_max*1.2)+1)
            ax.annotate(f'{current_height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, current_height),
                        xytext=(0, 2),  # 2 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    autolabel(bars)

    plt.tight_layout()

    return fig

def update_metrics():
    global monitor
    if monitor:
        # 更新各个画布
        update_io_stats(read_bytes_sec, write_bytes_sec)
        update_fps(fps)
        update_cpu_stats(package_cpu_usage, total_cpu_usage)

        # 每隔一段时间更新一次
        root.after(500, update_metrics)  # 每1000ms更新一次
    else:
        root.after(100, update_metrics)
    

def update_io_stats(read_bytes_sec, write_bytes_sec):
    """更新读写速率的柱状图"""
    global io_canvas  # 声明全局变量
    fig = plot_io_stats(read_bytes_sec, write_bytes_sec)
    io_canvas = update_canvas(fig, io_canvas)

def update_fps(fps):
    """更新FPS的柱状图"""
    global fps_canvas  # 声明全局变量
    fig = plot_fps(fps)
    fps_canvas = update_canvas(fig, fps_canvas)

def update_cpu_stats(package_cpu_usage, total_cpu_usage):
    """更新CPU使用率的柱状图"""
    global cpu_canvas  # 声明全局变量
    fig = plot_cpu_stats(package_cpu_usage, total_cpu_usage)
    cpu_canvas = update_canvas(fig, cpu_canvas)

def update_canvas(fig, canvas):
    """更新画布"""
    if canvas:
        canvas.get_tk_widget().destroy()  # 销毁旧的画布
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
    return canvas


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

    result = subprocess.run(["adb", "shell", f"dumpsys gfxinfo {package_name} framestats"], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    lines = result.stdout.splitlines()

    timestamps = []
    each_frame_timestamps = []
    isHaveFoundWindow = False
    PROFILEDATA_line = 0

    for line in lines:
        if "Window" in line and current_focus_window in line:
            isHaveFoundWindow = True
            continue
        if isHaveFoundWindow and "---PROFILEDATA---" in line:
            PROFILEDATA_line += 1
            continue
        if isHaveFoundWindow and "Flags,IntendedVsync," in line:
            continue
        if isHaveFoundWindow and (PROFILEDATA_line == 1):
            # 此处代表的是当前活动窗口
            # 我们取PROFILEDATA中间的数据 最多128帧，还可能包含之前重复的帧，所以我们间隔1.5s就取一次数据
            fields = []
            fields = line.split(",")
            each_frame_timestamp = [float(fields[1]), float(fields[13])]
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

def get_cpuinfo(package_name):
    """Get the cpuinfo."""

    result = subprocess.run(["adb", "shell", "dumpsys cpuinfo"], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    package_cpu_usage = 0
    total_cpu_usage = 0

    lines = result.stdout.splitlines()
    for line in lines:
        line = line.strip()
        pattern = r"^\d+(\.\d+)?%"
        result = re.match(pattern, line)
        if result and package_name in line:
            package_cpu_usage = float(line.split(" ")[0].replace("%",""))
        elif result and "TOTAL" in line:
            total_cpu_usage = float(line.split(" ")[0].replace("%",""))
        else:
            pass

    return package_cpu_usage,total_cpu_usage

def get_meminfo(package_name):
    """Get the memory used info."""
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

def start_to_Monitor(package_name,event_type, interval=0.5):
    global monitor,prev_timer,stop_threads
    if not monitor:
        prev_timer = time.time()    ###记录IO初始时间
        stop_threads = False
        start_monitor_thread(package_name,event_type,interval)
        start_monitor_touch_events_thread(event_type)
    else:
        log_message("Monitor is running")

def kill_thread():
    global monitor_thread, touch_thread, stop_threads, monitor, touch_processs
    stop_threads = True
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join()
    if touch_thread and touch_thread.is_alive():
        touch_process.kill()
        touch_thread.join()
    monitor = False
    log_message("Monitoring stopped.")


def open_root():
    global root, log_text, chart_frame, io_canvas, fps_canvas, cpu_canvas

    root = Tk()
    root.title("Android Monitor")
    root.geometry("1240x950")

    # package name combobox
    label1 = Label(root, text="package name:")
    label1.grid(row=0, column=0, sticky=NW, padx=10, pady=10)

    box1 = ttk.Combobox(root, width=50)
    box1['values'] = ('com.gxatek.cockpit.car.settings', 'com.gxatek.cockpit.weather', 'space.syncore.cockpit.map')
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


    # 创建各个画布
    io_canvas = None
    fps_canvas = None
    cpu_canvas = None

    update_io_stats(read_bytes_sec, write_bytes_sec)
    update_fps(fps)
    update_cpu_stats(package_cpu_usage, total_cpu_usage)
    update_metrics()    # 更新图表

    process_log_queue()  # 启动处理日志队列的定时器


    root.mainloop()

def monitor_io_and_fps(package_name,interval=0.5):
    global touchNum,monitor,chart_frame
    global read_bytes_sec,write_bytes_sec,fps,package_cpu_usage,total_cpu_usage ###绘图全局变量
    global prev_timer

    """Monitor the IO throughput and FPS of the given package name."""
    pid = get_pid(package_name)
    if not pid:
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
        read_bytes_sec = (read_bytes_diff / interval_time)/1024
        write_bytes_sec = (write_bytes_diff / interval_time)/1024
        prev_io_stats = current_io_stats
        prev_timer = current_timer
        log_message(f"Read: {read_bytes_sec:.1f} kBytes/s, Write: {write_bytes_sec:.1f} kBytes/s")
        
        fps,janky_frames = get_frame_stats(package_name,current_focus_window)
        if fps is None:
            log_message(f"FPS: N/A,{janky_frames}")
        else:
            log_message(f"FPS: {fps:.2f},{janky_frames}")
        
        ###CPU
        package_cpu_usage,total_cpu_usage = get_cpuinfo(package_name)# 读取CPU信息,return类型为list
        if package_cpu_usage == 0 and total_cpu_usage == 0:
            log_message(f"No vaild CPU info")
        else:
            log_message(f"{package_name} CPU usage:{package_cpu_usage:.1f}%,total CPU usage:{total_cpu_usage:.1f}%")
        

        ##内存
        meminfo = get_meminfo(package_name)# 读取内存使用情况,return类型为dict 
        if not meminfo:
            log_message(f"No vaild Memory info")
        else:
            log_message(f"Memory Usage infomation\tTotal PSS:{meminfo['TOTAL PSS']},\t\tTotal RSS:{meminfo['TOTAL RSS']},\t\tViews:{meminfo['Views']},\t\tActivities:{meminfo['Activities']}")

        log_message(f"Monitor: {touchNum} CPS\n")
        touchNum = 0 # 重置touchNum

def set_logging():
    ### 日志
    logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为DEBUG，意味着会记录所有级别的日志
    format='%(asctime)s - %(levelname)s - %(message)s',  # 设置日志输出格式
    filename=f'{current_time}.log',  # 设置日志文件名
    filemode='a'  # 追加模式（默认是'a'，即追加日志到文件末尾；'w'表示写模式，每次覆盖文件内容）
)

if __name__ == "__main__":
    global touchNum # 初始化touchNum
    touchNum = 0
    global monitor 
    monitor = False
    global read_bytes_sec
    global write_bytes_sec
    global fps
    global package_cpu_usage
    global total_cpu_usage 
    read_bytes_sec = write_bytes_sec  = package_cpu_usage = total_cpu_usage = 0 # 初始化绘图全局变量
    fps = 60.0
    global stop_threads 
    stop_threads = False
    global monitor_thread 
    monitor_thread = None
    global touch_thread
    touch_thread = None
    current_time = time.strftime('%Y-%m-%d %H_%M_%S', time.localtime())
    global prev_timer
    prev_timer = None
    global last_timestamp
    last_timestamp = 0
    

    set_logging()
    open_root()
                
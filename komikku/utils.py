import subprocess


def folder_size(path):
    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE)

    return res.stdout.split()[0].decode()


import inspect
import os
# import psutil
import time


def elapsed_since(start):
    elapsed = time.time() - start
    if elapsed < 1:
        return str(round(elapsed*1000, 2)) + "ms"
    if elapsed < 60:
        return str(round(elapsed, 2)) + "s"
    if elapsed < 3600:
        return str(round(elapsed / 60, 2)) + "min"
    else:
        return str(round(elapsed / 3600, 2)) + "hrs"


def format_bytes(bytes):
    if abs(bytes) < 1000:
        return str(bytes) + 'B'
    if abs(bytes) < 1e6:
        return str(round(bytes / 1e3, 2)) + 'kB'
    if abs(bytes) < 1e9:
        return str(round(bytes / 1e6, 2)) + 'MB'

    return str(round(bytes / 1e9, 2)) + 'GB'


# def get_process_memory():
#     process = psutil.Process(os.getpid())
#     # return process.memory_info()
# 
#     mi = process.memory_info()
#     return mi.rss, mi.vms, mi.shared
# 
# 
# def profile(func, *args, **kwargs):
#     def wrapper(*args, **kwargs):
#         rss_before, vms_before, shared_before = get_process_memory()
#         start = time.time()
#         result = func(*args, **kwargs)
#         elapsed_time = elapsed_since(start)
#         rss_after, vms_after, shared_after = get_process_memory()
#         print("Profiling: {:>20}  RES: {:>8} | VIRT: {:>8} | SHR {"
#               ":>9} | time: {:>8}"
#             .format("<" + func.__name__ + ">",
#                     format_bytes(rss_after),
#                     format_bytes(vms_after),
#                     format_bytes(shared_after),
#                     elapsed_time))
#         return result
#     if inspect.isfunction(func):
#         return wrapper
#     elif inspect.ismethod(func):
#         return wrapper(*args, **kwargs)
# 
# 
# def profile2(func, *args, **kwargs):
#     def wrapper(*args, **kwargs):
#         rss_before, vms_before, shared_before = get_process_memory()
#         start = time.time()
#         result = func(*args, **kwargs)
#         elapsed_time = elapsed_since(start)
#         rss_after, vms_after, shared_after = get_process_memory()
#         print("Profiling: {:>20}  RES: {:>8} | VIRT: {:>8} | SHR {"
#               ":>9} | time: {:>8}"
#             .format("<" + func.__name__ + ">",
#                     format_bytes(rss_after - rss_before),
#                     format_bytes(vms_after - vms_before),
#                     format_bytes(shared_after - shared_before),
#                     elapsed_time))
#         return result
#     if inspect.isfunction(func):
#         return wrapper
#     elif inspect.ismethod(func):
#         return wrapper(*args, **kwargs)
# 
# 
# def profile1(func):
#     def wrapper(*args, **kwargs):
#         mem_before = get_process_memory()
#         start = time.time()
#         result = func(*args, **kwargs)
#         elapsed_time = elapsed_since(start)
#         mem_after = get_process_memory()
# 
#         print('{}: memory before: {}, after: {}, consumed: {}; exec time: {}'.format(
#             func.__name__,
#             format_bytes(mem_before), format_bytes(mem_after), format_bytes(mem_after - mem_before),
#             elapsed_time))
# 
#         return result
# 
#     return wrapper

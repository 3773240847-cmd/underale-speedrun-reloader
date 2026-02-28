#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Undertale 重启工具 - 强制存档管理版
F1 - 极速重启游戏
F2 - 强制清除存档并重启
F6 - 强制更新存档并重启
"""

import os
import sys
import time
import subprocess
import zipfile
import shutil
import glob
import ctypes
import stat
from datetime import datetime
from functools import lru_cache

# 尝试导入必要的库
try:
    from keyboard import add_hotkey, wait
except ImportError:
    print("="*50)
    print("错误：缺少 keyboard 库")
    print("="*50)
    print("请运行：pip install keyboard psutil")
    input("\n按回车键退出...")
    sys.exit(1)

try:
    from psutil import process_iter, NoSuchProcess, AccessDenied
except ImportError:
    print("="*50)
    print("错误：缺少 psutil 库")
    print("="*50)
    print("请运行：pip install psutil")
    input("\n按回车键退出...")
    sys.exit(1)


class UndertaleReloader:
    """Undertale重启管理类（强制版）"""
    
    def __init__(self):
        """初始化"""
        # 游戏相关路径
        self.program_name = "undertale.exe"
        self.program_path = r"E:\UNDERTALE_V1.001_Linux\UNDERTALE.exe"
        self.game_dir = r"E:\UNDERTALE_V1.001_Linux"
        
        # 存档相关路径
        self.archive_path = r"C:\Users\Administrator\AppData\Local\UNDERTALE_linux_steamver\SAPC.zip"
        
        # 存档目录（使用 %localappdata%）
        self.localappdata = os.environ.get('LOCALAPPDATA', '')
        if not self.localappdata:
            # 如果环境变量不存在，使用默认路径
            self.localappdata = r"C:\Users\Administrator\AppData\Local"
        
        # Undertale 存档目录（在 Local 下）
        self.save_dir = os.path.join(self.localappdata, "UNDERTALE_linux_steamver")
        
        print(f"检测到 LocalAppData 路径: {self.localappdata}")
        print(f"存档目录: {self.save_dir}")
        
        # 缓存
        self._path_cache = {}
        self._process_cache = []
        self._last_process_check = 0
        self._process_cache_duration = 0.5
        
        # 快速检查路径
        self._quick_check_paths()
        
        # 检查管理员权限
        self._check_admin_rights()
    
    def _check_admin_rights(self):
        """检查管理员权限"""
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("\n⚠ 警告：当前不是管理员权限")
                print("  某些文件可能无法删除，建议以管理员身份运行")
            else:
                print("✓ 管理员权限：是")
        except:
            pass
    
    def _quick_check_paths(self):
        """快速路径检查"""
        print("\n" + "="*70)
        print("Undertale 强制存档管理工具")
        print("="*70)
        
        # 检查游戏程序
        if os.path.exists(self.program_path):
            print(f"✓ 游戏程序：{self.program_path}")
        else:
            print(f"✗ 游戏程序不存在：{self.program_path}")
            print("  请检查路径是否正确")
        
        # 检查游戏目录
        if os.path.exists(self.game_dir):
            print(f"✓ 游戏目录：{self.game_dir}")
        else:
            print(f"✗ 游戏目录不存在：{self.game_dir}")
        
        # 检查存档目录
        if os.path.exists(self.save_dir):
            print(f"✓ 存档目录：{self.save_dir}")
            # 检查写入权限
            if os.access(self.save_dir, os.W_OK):
                print(f"  ✓ 有写入权限")
            else:
                print(f"  ✗ 无写入权限，需要管理员权限")
            
            # 列出当前存档文件（只统计要删除的文件类型）
            save_files = self._get_save_files()
            
            if save_files:
                print(f"  当前有 {len(save_files)} 个存档文件")
                for f in sorted(save_files)[:5]:
                    size = os.path.getsize(os.path.join(self.save_dir, f)) / 1024
                    print(f"    - {f} ({size:.1f} KB)")
                if len(save_files) > 5:
                    print(f"    ... 等 {len(save_files)} 个文件")
            else:
                print(f"  当前没有存档文件")
            
            # 列出子文件夹（不会删除）
            subdirs = [d for d in os.listdir(self.save_dir) 
                      if os.path.isdir(os.path.join(self.save_dir, d))]
            if subdirs:
                print(f"  子文件夹（不会删除）：{', '.join(subdirs[:3])}")
        else:
            print(f"✗ 存档目录不存在：{self.save_dir}")
            print("  将创建存档目录")
        
        # 检查存档文件
        if os.path.exists(self.archive_path):
            archive_size = os.path.getsize(self.archive_path) / 1024
            print(f"✓ 存档包：{self.archive_path} ({archive_size:.1f} KB)")
            # 检查文件是否可读
            if os.access(self.archive_path, os.R_OK):
                print(f"  ✓ 可读取")
                
                # 显示ZIP内容
                try:
                    with zipfile.ZipFile(self.archive_path, 'r') as zf:
                        files = zf.namelist()
                        print(f"  存档包包含 {len(files)} 个文件")
                        for f in files[:3]:
                            print(f"    - {f}")
                except:
                    pass
            else:
                print(f"  ✗ 无法读取，权限不足")
        else:
            print(f"✗ 存档包不存在：{self.archive_path}")
            print("  请检查存档包路径是否正确")
        
        print("="*70)
    
    def _get_save_files(self):
        """获取所有要删除的存档文件（不包括子文件夹）"""
        if not os.path.exists(self.save_dir):
            return []
        
        save_files = []
        
        # 遍历存档目录中的所有文件（不包括子文件夹）
        for item in os.listdir(self.save_dir):
            item_path = os.path.join(self.save_dir, item)
            
            # 跳过子文件夹
            if os.path.isdir(item_path):
                continue
            
            # 检查文件类型
            filename = item.lower()
            
            # file 开头的文件
            if filename.startswith('file'):
                save_files.append(item)
            
            # system_information 开头的文件
            elif filename.startswith('system_information'):
                save_files.append(item)
            
            # .ini 后缀的文件
            elif filename.endswith('.ini'):
                save_files.append(item)
            
            # .dat 后缀的文件
            elif filename.endswith('.dat'):
                save_files.append(item)
        
        return save_files
    
    def _force_remove_file(self, file_path):
        """强制删除文件（处理只读、权限等问题）"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return True, "文件不存在"
            
            # 获取文件属性
            try:
                attrs = os.stat(file_path).st_file_attributes
            except:
                attrs = 0
            
            # 如果是只读文件，先移除只读属性
            if attrs & 1:  # FILE_ATTRIBUTE_READONLY
                try:
                    os.chmod(file_path, stat.S_IWRITE)
                except:
                    pass
            
            # 尝试删除
            os.remove(file_path)
            
            # 验证是否真的删除了
            if not os.path.exists(file_path):
                return True, "已删除"
            else:
                return False, "删除后文件仍然存在"
                
        except PermissionError:
            return False, "权限不足"
        except Exception as e:
            return False, str(e)
    
    def find_undertale_processes_force(self):
        """强制查找所有Undertale相关进程"""
        processes = []
        try:
            # 查找所有可能的Undertale进程
            for proc in process_iter(['name', 'pid', 'exe']):
                try:
                    proc_name = proc.info['name'] or ""
                    proc_exe = proc.info['exe'] or ""
                    
                    # 检查进程名
                    if self.program_name in proc_name.lower():
                        processes.append(proc)
                    # 检查完整路径
                    elif self.program_path.lower() in proc_exe.lower():
                        processes.append(proc)
                except (NoSuchProcess, AccessDenied):
                    pass
        except Exception:
            pass
        
        return processes
    
    def close_undertale_force(self):
        """强制关闭所有Undertale相关进程"""
        print("  - 正在强制关闭游戏进程...")
        
        # 方法1: 使用taskkill强制关闭
        if os.name == 'nt':
            try:
                subprocess.run(['taskkill', '/f', '/im', self.program_name], 
                             capture_output=True, timeout=2)
            except:
                pass
        
        # 方法2: 查找并终止所有相关进程
        processes = self.find_undertale_processes_force()
        killed = []
        
        for proc in processes:
            try:
                proc_name = proc.info['name']
                proc_pid = proc.info['pid']
                proc.kill()
                killed.append(f"{proc_name}({proc_pid})")
            except:
                pass
        
        if killed:
            print(f"    ✓ 已终止 {len(killed)} 个进程")
        else:
            print("    - 没有找到运行中的进程")
        
        # 等待进程完全退出
        time.sleep(1)
        
        return True
    
    def force_clear_all_saves(self):
        """强制清除存档目录中的指定文件（不包括子文件夹）"""
        print("  - 正在强制清除存档文件...")
        
        if not os.path.exists(self.save_dir):
            print(f"    - 存档目录不存在，无需清除")
            return False
        
        # 获取要删除的文件列表
        save_files = self._get_save_files()
        
        if not save_files:
            print(f"    - 没有找到需要删除的存档文件")
            return False
        
        deleted_files = []
        failed_files = []
        
        # 删除每个文件
        for filename in save_files:
            file_path = os.path.join(self.save_dir, filename)
            success, msg = self._force_remove_file(file_path)
            if success:
                deleted_files.append(filename)
                print(f"      ✓ 已删除: {filename}")
            else:
                failed_files.append(f"{filename} ({msg})")
                print(f"      ✗ 删除失败: {filename} - {msg}")
        
        # 最终报告
        print(f"    ✓ 成功删除 {len(deleted_files)} 个存档文件")
        if failed_files:
            print(f"    ⚠ {len(failed_files)} 个文件删除失败")
        
        return len(deleted_files) > 0
    
    def force_extract_archive(self):
        """强制解压存档到存档目录（只解压文件，不包括子文件夹结构）"""
        print("  - 正在强制解压存档...")
        
        # 检查存档文件
        if not os.path.exists(self.archive_path):
            print(f"    ✗ 存档包不存在: {self.archive_path}")
            return False
        
        try:
            # 验证ZIP文件
            with zipfile.ZipFile(self.archive_path, 'r') as test_zip:
                # 测试ZIP是否损坏
                bad_file = test_zip.testzip()
                if bad_file:
                    print(f"    ✗ 存档包损坏: {bad_file}")
                    return False
                
                file_list = test_zip.namelist()
                # 过滤出文件（排除目录）
                file_list = [f for f in file_list if not f.endswith('/')]
                print(f"    - 存档包包含 {len(file_list)} 个文件")
                for f in file_list[:3]:
                    print(f"      - {f}")
            
            # 确保存档目录存在
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir)
                print(f"    - 创建存档目录: {self.save_dir}")
            
            # 解压文件到存档目录（保持原有文件名）
            extracted_count = 0
            with zipfile.ZipFile(self.archive_path, 'r') as zip_ref:
                for file in file_list:
                    # 获取文件名（去掉可能的路径）
                    filename = os.path.basename(file)
                    if not filename:  # 如果是目录，跳过
                        continue
                    
                    # 读取文件内容并写入到目标目录
                    source = zip_ref.read(file)
                    target_path = os.path.join(self.save_dir, filename)
                    
                    with open(target_path, 'wb') as f:
                        f.write(source)
                    
                    extracted_count += 1
                    if extracted_count <= 3:  # 只显示前3个
                        print(f"      ✓ 解压: {filename}")
            
            print(f"    ✓ 成功解压 {extracted_count} 个文件到存档目录")
            return extracted_count > 0
                
        except zipfile.BadZipFile:
            print(f"    ✗ 存档包损坏（不是有效的ZIP文件）")
            return False
        except Exception as e:
            print(f"    ✗ 解压出错: {e}")
            return False
    
    def start_undertale_force(self):
        """强制启动Undertale"""
        if not os.path.exists(self.program_path):
            print(f"    ✗ 找不到游戏程序")
            return False
        
        try:
            if os.name == 'nt':
                os.startfile(self.program_path)
            else:
                subprocess.Popen([self.program_path], cwd=self.game_dir)
            
            print(f"    ✓ 游戏启动命令已执行")
            return True
                
        except Exception as e:
            print(f"    ✗ 启动失败: {e}")
            return False
    
    def quick_reload(self):
        """F1 - 极速重启"""
        print("\n" + "="*70)
        print("F1: 极速重启")
        print("="*70)
        
        # 关闭游戏
        self.close_undertale_force()
        
        # 启动游戏
        time.sleep(0.2)
        self.start_undertale_force()
        
        print("="*70)
        print("重启完成！")
        print("="*70)
    
    def force_clear_and_reload(self):
        """F2 - 强制清除存档并重启"""
        print("\n" + "="*70)
        print("F2: 强制清除存档并重启")
        print("="*70)
        
        # 强制关闭游戏
        self.close_undertale_force()
        time.sleep(0.5)
        
        # 强制清除指定类型的存档文件（不包括子文件夹）
        clear_success = self.force_clear_all_saves()
        
        # 等待一下
        time.sleep(0.3)
        
        # 启动游戏
        self.start_undertale_force()
        
        print("="*70)
        if clear_success:
            print("存档强制清除完成，游戏已重启！")
        else:
            print("没有找到存档文件，游戏已重启")
        print("="*70)
    
    def force_reload_with_archive(self):
        """F6 - 强制更新存档并重启"""
        print("\n" + "="*70)
        print("F6: 强制更新存档并重启")
        print("="*70)
        
        # 强制关闭游戏
        self.close_undertale_force()
        time.sleep(0.5)
        
        # 强制清除指定类型的旧存档文件（不包括子文件夹）
        self.force_clear_all_saves()
        time.sleep(0.3)
        
        # 强制解压新存档到存档目录（只解压文件，不创建子文件夹）
        extract_success = self.force_extract_archive()
        
        # 等待一下
        time.sleep(0.3)
        
        # 启动游戏
        self.start_undertale_force()
        
        print("="*70)
        if extract_success:
            print("存档强制更新完成，游戏已重启！")
        else:
            print("⚠ 存档更新失败，但游戏已重启")
        print("="*70)


def main():
    """主函数"""
    print("="*70)
    print("Undertale 强制存档管理工具")
    print("="*70)
    print("\n热键功能：")
    print("  F1 - 极速重启")
    print("  F2 - 强制清除存档并重启")
    print("  F6 - 强制更新存档并重启")
    print("="*70)
    print("\n存档位置：")
    print(f"  %localappdata%\\UNDERTALE_linux_steamver")
    print(f"  {os.environ.get('LOCALAPPDATA', '')}\\UNDERTALE_linux_steamver")
    print("="*70)
    print("\n删除的文件类型：")
    print("  • file 开头的文件")
    print("  • system_information 开头的文件")
    print("  • .ini 后缀的文件")
    print("  • .dat 后缀的文件")
    print("\n不会删除：")
    print("  • 子文件夹及其内容")
    print("  • 其他类型的文件")
    print("="*70)
    
    # 创建实例
    reloader = UndertaleReloader()
    
    # 注册热键 - 只有F1、F2、F6
    try:
        add_hotkey('f1', reloader.quick_reload)
        add_hotkey('f2', reloader.force_clear_and_reload)
        add_hotkey('f6', reloader.force_reload_with_archive)
        print("\n✓ 热键注册成功")
    except Exception as e:
        print(f"\n✗ 热键注册失败: {e}")
        print("请以管理员身份运行")
        input("按回车键退出...")
        return
    
    print("\n等待按键...")
    
    # 无限循环
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
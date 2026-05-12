import os
import subprocess
import shutil
import sys
from typing import List, Dict, Any

# --- 路径配置 ---
BASE_DIR = 'dist'
ARCH_X64 = os.path.join(BASE_DIR, 'x64')
ARCH_ARM64 = os.path.join(BASE_DIR, 'arm64')
UNIVERSAL_DIR = os.path.join(BASE_DIR, 'universal')

REPORTS = {
    "full": os.path.join(BASE_DIR, "build_report_full.md"),
    "binary": os.path.join(BASE_DIR, "build_report_binary.md")
}

class UniversalBuilder:
    def __init__(self):
        # 内部存储审计数据，实现逻辑与展示分离
        self.audit_log: List[Dict[str, Any]] = []

    def _is_macho(self, path: str) -> bool:
        """
        严谨判定：仅针对 Mach-O 二进制文件（可执行文件、动态库、Framework 核心）
        """
        try:
            # 只有 file 命令返回包含 Mach-O 的才是真正的二进制
            out = subprocess.check_output(['file', path], stderr=subprocess.DEVNULL).decode('utf-8')
            return 'Mach-O' in out
        except:
            return False

    def _get_arch_info(self, path: str) -> List[str]:
        """获取 lipo 信息"""
        try:
            out = subprocess.check_output(['lipo', '-info', path], stderr=subprocess.DEVNULL).decode('utf-8')
            return out.split(':')[-1].strip().split()
        except:
            return []

    def setup_env(self):
        """初始化环境"""
        print("[*] Initializing Environment...")
        if not (os.path.exists(ARCH_X64) and os.path.exists(ARCH_ARM64)):
            print("[!] Fatal: x64 or arm64 source directory missing."); sys.exit(1)
        
        if os.path.exists(UNIVERSAL_DIR):
            shutil.rmtree(UNIVERSAL_DIR)
        
        # 基础复制：先以 x64 为模版构建并集树
        shutil.copytree(ARCH_X64, UNIVERSAL_DIR, symlinks=True)

    def execute_union_merge(self):
        """核心策略：并集合并"""
        print("[[*] Step 1: Merging missing assets from arm64...")
        # 补齐 arm64 特有的文件（例如 v8_context_snapshot.arm64.bin）
        for root, _, files in os.walk(ARCH_ARM64):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, ARCH_ARM64)
                dst = os.path.join(UNIVERSAL_DIR, rel)
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)

        print("[[*] Step 2: Processing binaries with Lipo...")
        for root, _, files in os.walk(UNIVERSAL_DIR):
            for f in files:
                uni_path = os.path.join(root, f)
                rel_path = os.path.relpath(uni_path, UNIVERSAL_DIR)
                
                x64_src = os.path.join(ARCH_X64, rel_path)
                arm_src = os.path.join(ARCH_ARM64, rel_path)
                
                ex_x64, ex_arm = os.path.exists(x64_src), os.path.exists(arm_src)
                macho_flag = self._is_macho(uni_path)
                
                status = "Copied"
                note = "-"

                if ex_x64 and ex_arm:
                    if os.path.islink(uni_path):
                        note = "Symlink"
                    elif macho_flag:
                        # 检查是否已经是通用二进制
                        archs = self._get_arch_info(x64_src)
                        if 'x86_64' in archs and 'arm64' in archs:
                            status = "✅ Already Uni"
                        else:
                            # 执行 lipo 合并
                            res = subprocess.run(['lipo', '-create', x64_src, arm_src, '-output', uni_path], capture_output=True, text=True)
                            if res.returncode == 0:
                                status = "✅ Merged"
                                note = "Lipo Success"
                            else:
                                status = "❌ FAIL"
                                note = res.stderr.strip()
                    else:
                        note = "Shared Resource"
                else:
                    note = "Arch-Specific Asset"

                self.audit_log.append({
                    "name": rel_path,
                    "is_bin": macho_flag,
                    "x64": ex_x64,
                    "arm64": ex_arm,
                    "status": status,
                    "note": note
                })

    def generate_reports(self):
        """生成双重审计报告"""
        print("[*] Generating audit reports...")
        header = "| File Name | Is Mach-O | x64 | arm64 | Universal | Note |\n| :--- | :---: | :---: | :---: | :---: | :--- |"
        
        def format_row(i):
            return f"| {i['name']} | {'**YES**' if i['is_bin'] else 'no'} | {'✅' if i['x64'] else '❌'} | {'✅' if i['arm64'] else '❌'} | {i['status']} | {i['note']} |"

        # 1. 全量报告
        with open(REPORTS['full'], 'w', encoding='utf-8') as f:
            f.write("# Full Build Audit Report\n\n" + header + "\n" + "\n".join([format_row(i) for i in self.audit_log]))

        # 2. 仅 Mach-O 报告 (Binary Only)
        with open(REPORTS['binary'], 'w', encoding='utf-8') as f:
            binary_only = [format_row(i) for i in self.audit_log if i['is_bin']]
            f.write("# Binary Assets Audit Report (Mach-O Only)\n\n" + header + "\n" + "\n".join(binary_only))

    def run(self):
        self.setup_env()
        self.execute_union_merge()
        self.generate_reports()
        print(f"\n[✔] 构建成功。通用二进制产物位于: {UNIVERSAL_DIR}")

if __name__ == "__main__":
    builder = UniversalBuilder()
    builder.run()
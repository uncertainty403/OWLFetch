#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import getpass
import socket
import re
import qrcode
import argparse
from pathlib import Path

class Colors:
    BLACK = '\033[0;30m'
    DARK_GRAY = '\033[1;30m'
    LIGHT_GRAY = '\033[0;37m'
    WHITE = '\033[1;37m'
    BLUE = '\033[0;34m'
    LIGHT_BLUE = '\033[1;34m'
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    PURPLE = '\033[0;35m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;213m'
    NC = '\033[0m'

class Theme:
    PRIMARY = Colors.WHITE
    SECONDARY = Colors.LIGHT_GRAY
    ACCENT = Colors.LIGHT_BLUE
    BORDER = Colors.DARK_GRAY

class SystemInfo:
    @staticmethod
    def run_cmd(cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""

    @staticmethod
    def read_file(path):
        try:
            return Path(path).read_text().strip()
        except:
            return ""

    def get_os_info(self):
        if not Path('/etc/os-release').exists():
            return "Unknown Linux"
        
        content = self.read_file('/etc/os-release')
        for line in content.split('\n'):
            if line.startswith('PRETTY_NAME='):
                return line.split('=')[1].strip('"')
        return "Unknown Linux"

    def get_kernel_info(self):
        return self.run_cmd('uname -r')

    def get_hostname(self):
        return socket.gethostname()

    def get_uptime(self):
        uptime_content = self.read_file('/proc/uptime')
        if not uptime_content:
            return "Unknown"
        
        uptime_sec = int(float(uptime_content.split()[0]))
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60
        
        if days > 0:
            return f"up {days} days, {hours} hours, {minutes} minutes"
        elif hours > 0:
            return f"up {hours} hours, {minutes} minutes"
        else:
            return f"up {minutes} minutes"

    def get_shell_info(self):
        return os.path.basename(os.environ.get('SHELL', 'Unknown'))

    def get_resolution(self):
        if 'DISPLAY' not in os.environ:
            return "Unknown"
        
        res = self.run_cmd("xrandr 2>/dev/null | grep '*' | awk '{print $1}' | head -n1")
        return res or "Unknown"

    def get_desktop_environment(self):
        return (os.environ.get('XDG_CURRENT_DESKTOP') or 
                os.environ.get('DESKTOP_SESSION') or 
                os.environ.get('GDMSESSION') or 
                "Unknown")

    def get_cpu_info(self):
        if not Path('/proc/cpuinfo').exists():
            return "Unknown CPU"
        
        content = self.read_file('/proc/cpuinfo')
        for line in content.split('\n'):
            if line.startswith('model name'):
                cpu_info = line.split(':')[1].strip()
                cpu_info = re.sub(r'\(R\)|\(TM\)|CPU @ .*', '', cpu_info)
                cpu_info = re.sub(r'  +', ' ', cpu_info)
                return cpu_info or "Unknown CPU"
        return "Unknown CPU"

    def get_cpu_usage(self):
        if not Path('/proc/stat').exists():
            return "0"
        
        content = self.read_file('/proc/stat')
        for line in content.split('\n'):
            if line.startswith('cpu '):
                values = list(map(int, line.split()[1:]))
                idle = values[3]
                total = sum(values)
                usage = 100 - (idle * 100 // total)
                return str(usage)
        return "0"

    def get_cpu_temp(self):
        temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
        if not temp_file.exists():
            return "N/A"
        
        temp_raw = self.read_file(str(temp_file))
        if temp_raw and int(temp_raw) > 0:
            return f"{int(temp_raw) // 1000}°C"
        return "N/A"

    def get_gpu_info(self):
        if not Path('/proc/devices').exists():
            return "Unknown GPU"
        
        gpu_info = self.run_cmd("lspci | grep -i 'vga\\|3d\\|2d' | head -n1 | cut -d ':' -f3 | sed 's/^[ \\t]*//'")
        return gpu_info or "Unknown GPU"

    def get_memory_info(self):
        if not Path('/proc/meminfo').exists():
            return "Unknown"
        
        content = self.read_file('/proc/meminfo')
        total_mem = avail_mem = 0
        
        for line in content.split('\n'):
            if line.startswith('MemTotal:'):
                total_mem = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                avail_mem = int(line.split()[1])
        
        if total_mem and avail_mem:
            used_mem = total_mem - avail_mem
            total_gb = total_mem // 1024 // 1024
            used_gb = used_mem // 1024 // 1024
            percentage = used_mem * 100 // total_mem
            return f"{used_gb}GB / {total_gb}GB ({percentage}%)"
        return "Unknown"

    def get_disk_info(self):
        disk_info = self.run_cmd("df -h / 2>/dev/null | awk 'NR==2{print $3 \" / \" $2 \" (\" $5 \")\"}'")
        return disk_info or "Unknown"

    def get_battery_info(self):
        capacity_file = Path('/sys/class/power_supply/BAT0/capacity')
        status_file = Path('/sys/class/power_supply/BAT0/status')
        
        if not capacity_file.exists():
            return None
        
        capacity = self.read_file(str(capacity_file))
        status = self.read_file(str(status_file))
        
        if capacity:
            return f"{capacity}% [{status}]"
        return None

    def get_locale_info(self):
        return os.environ.get('LANG', 'Unknown')

    def get_packages_info(self):
        package_managers = [
            ('/var/lib/dpkg/status', "grep -c '^Package:' /var/lib/dpkg/status 2>/dev/null"),
            ('/var/lib/rpm', "find /var/lib/rpm -name '*.rpm' 2>/dev/null | wc -l"),
            ('/var/lib/pacman/local', "find /var/lib/pacman/local -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l")
        ]
        
        for path, cmd in package_managers:
            if Path(path).exists():
                packages = self.run_cmd(cmd)
                if packages:
                    return packages
        return "0"

    def get_network_info(self):
        if not Path('/proc/net/route').exists():
            return "No connection"
        
        network = self.run_cmd("awk '$2 == \"00000000\" {print $1}' /proc/net/route | head -n1")
        if network:
            ip_addr = self.run_cmd(f"ip addr show {network} 2>/dev/null | grep 'inet ' | awk '{{print $2}}' | cut -d'/' -f1 | head -n1")
            return f"{network} ({ip_addr or 'Unknown IP'})"
        return "No connection"

    def get_load_average(self):
        if not Path('/proc/loadavg').exists():
            return "Unknown"
        
        content = self.read_file('/proc/loadavg')
        return ' '.join(content.split()[:3])

class LogoGenerator:
    def __init__(self):
        self.accent = Theme.ACCENT
        self.nc = Colors.NC

    def get_compact_logo(self):
        return f"""    {self.accent}▓▓▓▓▓▓{self.nc}
   {self.accent}▓▓▓▓▓▓▓▓{self.nc}
  {self.accent}▓▓██▓▓██▓▓{self.nc}
  {self.accent}▓▓▓▓▓▓▓▓▓▓{self.nc}
   {self.accent}▓▓▓▓▓▓▓▓{self.nc}
    {self.accent}▓▓▓▓▓▓{self.nc}""".split('\n')

    def get_full_logo(self):
        return f"""        {self.accent}░ ░░░░                            ░░░░░░{self.nc}
        {self.accent}░░░░░░                            ░░░░░░{self.nc}
        {self.accent}░░░▓▓░░░░   ░░░░░░░░░░░░░░░░░  ░░░░▒▒░░{self.nc}
         {self.accent}░░▓▓▓▓▓▓░░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░░▒▒▒▒▒▒░░{self.nc}
           {self.accent}░▓▓▓▓▓▓▓▓▓░░░▒▒▒▒▒▒▒▒░░░▒▒▒▒▒▒▒▒▒▒░{self.nc}
           {self.accent}░░▓▓▓▓▓▓▓▓▓▓▒░░▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒░░{self.nc}
        {self.accent}░░░▒▓▓░░░░░░░░░▓▓░░▒▒░░▒▒░░░░░░░░░▒▒░░░░{self.nc}
        {self.accent}░░▓▓▓░   ░██░░░░▓▓░░░▒▒▒░░▒░██░░░░░▒▒▒░░{self.nc}
        {self.accent}░░▓▓░░ ░░██░░░█░░▓▓░░▒▒░░▒░░░██░  ░░▒▒░{self.nc}
        {self.accent}░░▓▓░  ░░███▓█▓░░▓▓░░▒▒░░██▓███░░ ░░▒▒░░{self.nc}
        {self.accent}░░▓▓░░   ░░█▓░░░░▓▓░░▒▒░░░░▓█░░   ░░▒▒░░{self.nc}
         {self.accent}░░▓▓░░░░  ░░░░▒▓▓░░░░▒▒░░░░░░  ░░░░▒▒░░░{self.nc}
        {self.accent}░░░░▓▓▓▓░░░░░▓▓▓▒░░▒▒░░▒▒▒▒░░░░░▒▒▒▒░░░░{self.nc}
           {self.accent}░░░░▓▓▓▓▓▓▒░░░░░▒▒░░░░░▒▒▒▒▒▒▒░░░░{self.nc}
           {self.accent}░░░▒▒░░░░░▒▒▒▒▒░░░░▒▒▒▒▒░░░░░▒▒░░░{self.nc}
           {self.accent}░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░{self.nc}
              {self.accent}░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░{self.nc}
                 {self.accent}░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░{self.nc}
                 {self.accent}░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░{self.nc}
                   {self.accent}░░░░▒▒▒▒▒▒▒▒▒▒░░░░{self.nc}
                      {self.accent}░░░▒▒▒▒▒▒░░░{self.nc}
                      {self.accent}░░░░░▒▒░░░░░{self.nc}
                         {self.accent}░░░░░░{self.nc}""".split('\n')

    def generate_ascii_qr(self, url):
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            matrix = qr.get_matrix()
            ascii_qr = []
            
            for row in matrix:
                line = ""
                for cell in row:
                    line += f"{self.accent}██{self.nc}" if cell else "  "
                ascii_qr.append(line)
            
            return ascii_qr
        except ImportError:
            return [f"{Colors.RED}Error: qrcode library not installed{Colors.NC}",
                    f"{Theme.SECONDARY}Install with: pip install qrcode[pil]{Colors.NC}"]
        except Exception as e:
            return [f"{Colors.RED}Error generating QR code: {str(e)}{Colors.NC}"]

class Display:
    def __init__(self):
        self.system_info = SystemInfo()
        self.logo_generator = LogoGenerator()

    def get_terminal_size(self):
        try:
            return shutil.get_terminal_size()
        except:
            return shutil.get_terminal_size((80, 24))

    def get_string_length(self, text):
        return len(re.sub(r'\x1b\[[0-9;]*m', '', text))

    def safe_truncate(self, text, max_len):
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        if len(clean_text) <= max_len:
            return text
        
        truncated = ""
        visible_len = 0
        i = 0
        
        while i < len(text) and visible_len < max_len - 3:
            if text[i:i+1] == '\033':
                end = text.find('m', i)
                if end != -1:
                    truncated += text[i:end+1]
                    i = end + 1
                else:
                    i += 1
            else:
                truncated += text[i]
                visible_len += 1
                i += 1
        
        return truncated + "..."

    def build_info_lines(self, max_text_length):
        si = self.system_info
        username = getpass.getuser()
        hostname = si.get_hostname()
        
        info_lines = [
            f"{Theme.PRIMARY}{username}{Theme.SECONDARY}@{Theme.ACCENT}{hostname}{Colors.NC}",
            f"{Theme.BORDER}{'─' * min(30, max_text_length)}{Colors.NC}",
            f"{Theme.ACCENT}󰍹 {Theme.PRIMARY}System{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}OS{Colors.NC}         {self.safe_truncate(f'{Theme.SECONDARY}{si.get_os_info()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Kernel{Colors.NC}     {self.safe_truncate(f'{Theme.SECONDARY}{si.get_kernel_info()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Uptime{Colors.NC}     {self.safe_truncate(f'{Theme.SECONDARY}{si.get_uptime()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Packages{Colors.NC}   {Theme.SECONDARY}{si.get_packages_info()}{Colors.NC}",
            f"{Theme.ACCENT}└─ {Theme.PRIMARY}Shell{Colors.NC}      {Theme.SECONDARY}{si.get_shell_info()}{Colors.NC}",
            "",
            f"{Theme.ACCENT}󰍹 {Theme.PRIMARY}Hardware{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}CPU{Colors.NC}        {self.safe_truncate(f'{Theme.SECONDARY}{si.get_cpu_info()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}GPU{Colors.NC}        {self.safe_truncate(f'{Theme.SECONDARY}{si.get_gpu_info()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Memory{Colors.NC}     {Theme.SECONDARY}{si.get_memory_info()}{Colors.NC}",
            f"{Theme.ACCENT}└─ {Theme.PRIMARY}Disk{Colors.NC}       {Theme.SECONDARY}{si.get_disk_info()}{Colors.NC}",
            "",
            f"{Theme.ACCENT}󰍹 {Theme.PRIMARY}Performance{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}CPU Usage{Colors.NC}  {Theme.SECONDARY}{si.get_cpu_usage()}%{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}CPU Temp{Colors.NC}   {Theme.SECONDARY}{si.get_cpu_temp()}{Colors.NC}",
            f"{Theme.ACCENT}└─ {Theme.PRIMARY}Load Avg{Colors.NC}   {Theme.SECONDARY}{si.get_load_average()}{Colors.NC}",
            "",
            f"{Theme.ACCENT}󰍹 {Theme.PRIMARY}Environment{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}DE/WM{Colors.NC}      {self.safe_truncate(f'{Theme.SECONDARY}{si.get_desktop_environment()}{Colors.NC}', max_text_length - 15)}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Resolution{Colors.NC} {Theme.SECONDARY}{si.get_resolution()}{Colors.NC}",
            f"{Theme.ACCENT}├─ {Theme.PRIMARY}Locale{Colors.NC}     {Theme.SECONDARY}{si.get_locale_info()}{Colors.NC}",
            f"{Theme.ACCENT}└─ {Theme.PRIMARY}Network{Colors.NC}    {self.safe_truncate(f'{Theme.SECONDARY}{si.get_network_info()}{Colors.NC}', max_text_length - 15)}"
        ]
        
        battery = si.get_battery_info()
        if battery:
            info_lines.extend([
                "",
                f"{Theme.ACCENT}󰁹 {Theme.PRIMARY}Battery{Colors.NC}    {Theme.SECONDARY}{battery}{Colors.NC}"
            ])
        
        if max_text_length > 40:
            info_lines.extend([
                "",
                f"{Theme.SECONDARY}Colors: {Colors.BLACK}███{Colors.RED}███{Colors.GREEN}███{Colors.YELLOW}███{Colors.BLUE}███{Colors.PURPLE}███{Colors.CYAN}███{Colors.WHITE}███{Colors.NC}"
            ])
        
        return info_lines

    def render(self, ascii_qr_url=None):
        os.system('clear')
        
        term_cols, term_rows = self.get_terminal_size()
        
        if ascii_qr_url:
            logo_lines = self.logo_generator.generate_ascii_qr(ascii_qr_url)
        else:
            logo_lines = (self.logo_generator.get_compact_logo() if term_cols < 80 
                         else self.logo_generator.get_full_logo())
        
        max_logo_width = max(self.get_string_length(line) for line in logo_lines) if logo_lines else 0
        padding = 4
        max_text_length = term_cols - max_logo_width - padding
        
        if max_text_length < 30:
            max_text_length = 30
        
        info_lines = self.build_info_lines(max_text_length)
        
        if term_cols < 60:
            print()
            for line in info_lines:
                print(line)
            print()
            return
        
        max_lines = max(len(logo_lines), len(info_lines))
        
        print()
        for i in range(max_lines):
            if i < len(logo_lines):
                print(logo_lines[i], end='')
                current_width = self.get_string_length(logo_lines[i])
                spaces_needed = max_logo_width - current_width + padding
            else:
                spaces_needed = max_logo_width + padding
            
            print(' ' * spaces_needed, end='')
            
            if i < len(info_lines):
                print(info_lines[i])
            else:
                print()
        
        print()

def main():
    parser = argparse.ArgumentParser(description='OWLFetch — система информации')
    parser.add_argument('--ascii-qr', type=str, help='Генерировать ASCII QR-код')
    args = parser.parse_args()
    
    display = Display()
    display.render(args.ascii_qr)

if __name__ == "__main__":
    main()
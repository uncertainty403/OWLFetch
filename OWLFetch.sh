#!/bin/bash

BLACK='\033[0;30m'
DARK_GRAY='\033[1;30m'
LIGHT_GRAY='\033[0;37m'
WHITE='\033[1;37m'
BLUE='\033[0;34m'
LIGHT_BLUE='\033[1;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
ORANGE='\033[38;5;208m'
PINK='\033[38;5;213m'
NC='\033[0m'

PRIMARY=$WHITE
SECONDARY=$LIGHT_GRAY
ACCENT=$LIGHT_BLUE
BORDER=$DARK_GRAY



get_string_length() {
    local clean_string=$(echo -e "$1" | sed -r 's/\x1b\[[0-9;]*m//g')
    echo "${#clean_string}"
}

get_os_info() {
    local os_info=""
    if [ -f /etc/os-release ]; then
        os_info=$(grep PRETTY_NAME /etc/os-release | cut -d '=' -f2 | tr -d '"')
    fi
    echo "${os_info:-Unknown Linux}"
}

get_kernel_info() {
    uname -r
}

get_hostname() {
    hostname
}

get_uptime() {
    local uptime_sec=$(cat /proc/uptime | cut -d. -f1)
    local days=$((uptime_sec / 86400))
    local hours=$(((uptime_sec % 86400) / 3600))
    local minutes=$(((uptime_sec % 3600) / 60))
    
    if [ $days -gt 0 ]; then
        echo "up $days days, $hours hours, $minutes minutes"
    elif [ $hours -gt 0 ]; then
        echo "up $hours hours, $minutes minutes"
    else
        echo "up $minutes minutes"
    fi
}

get_shell_info() {
    basename "$SHELL"
}

get_resolution() {
    local res=""
    if [ -n "$DISPLAY" ] && command -v xrandr >/dev/null 2>&1; then
        res=$(xrandr 2>/dev/null | grep '*' | awk '{print $1}' | head -n1)
    fi
    echo "${res:-Unknown}"
}

get_desktop_environment() {
    local de=""
    if [ -n "$XDG_CURRENT_DESKTOP" ]; then
        de="$XDG_CURRENT_DESKTOP"
    elif [ -n "$DESKTOP_SESSION" ]; then
        de="$DESKTOP_SESSION"
    elif [ -n "$GDMSESSION" ]; then
        de="$GDMSESSION"
    fi
    echo "${de:-Unknown}"
}

get_cpu_info() {
    if [ -f /proc/cpuinfo ]; then
        local cpu_info=$(grep -m 1 'model name' /proc/cpuinfo | cut -d ':' -f 2 | sed 's/^[ \t]*//')
        cpu_info=$(echo "$cpu_info" | sed 's/(R)//g' | sed 's/(TM)//g' | sed 's/CPU @ .*//g' | sed 's/  */ /g')
        echo "${cpu_info:-Unknown CPU}"
    else
        echo "Unknown CPU"
    fi
}

get_cpu_usage() {
    if [ -f /proc/stat ]; then
        local cpu_line=$(grep '^cpu ' /proc/stat)
        local idle=$(echo $cpu_line | awk '{print $5}')
        local total=$(echo $cpu_line | awk '{print $2+$3+$4+$5+$6+$7+$8}')
        local usage=$((100 - (idle * 100) / total))
        echo "$usage"
    else
        echo "0"
    fi
}

get_cpu_temp() {
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        local temp_raw=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
        if [ -n "$temp_raw" ] && [ "$temp_raw" -gt 0 ]; then
            echo "$((temp_raw / 1000))°C"
        else
            echo "N/A"
        fi
    else
        echo "N/A"
    fi
}

get_gpu_info() {
    if [ -f /proc/devices ] && command -v lspci >/dev/null 2>&1; then
        local gpu_info=$(lspci | grep -i 'vga\|3d\|2d' | head -n1 | cut -d ':' -f3 | sed 's/^[ \t]*//')
        echo "${gpu_info:-Unknown GPU}"
    else
        echo "Unknown GPU"
    fi
}

get_memory_info() {
    if [ -f /proc/meminfo ]; then
        local total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local avail_mem=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        local used_mem=$((total_mem - avail_mem))
        
        local total_gb=$((total_mem / 1024 / 1024))
        local used_gb=$((used_mem / 1024 / 1024))
        local percentage=$((used_mem * 100 / total_mem))
        
        echo "${used_gb}GB / ${total_gb}GB (${percentage}%)"
    else
        echo "Unknown"
    fi
}

get_disk_info() {
    local disk_info=$(df -h / 2>/dev/null | awk 'NR==2{print $3 " / " $2 " (" $5 ")"}')
    echo "${disk_info:-Unknown}"
}

get_battery_info() {
    if [ -f /sys/class/power_supply/BAT0/capacity ]; then
        local capacity=$(cat /sys/class/power_supply/BAT0/capacity 2>/dev/null)
        local status=$(cat /sys/class/power_supply/BAT0/status 2>/dev/null)
        if [ -n "$capacity" ]; then
            echo "${capacity}% [${status}]"
        fi
    fi
}

get_locale_info() {
    local locale_info=$(locale 2>/dev/null | grep LANG= | cut -d= -f2)
    echo "${locale_info:-Unknown}"
}

get_packages_info() {
    local packages="0"
    
    if [ -f /var/lib/dpkg/status ]; then
        packages=$(grep -c '^Package:' /var/lib/dpkg/status 2>/dev/null)
    elif [ -d /var/lib/rpm ]; then
        packages=$(find /var/lib/rpm -name "*.rpm" 2>/dev/null | wc -l)
    elif [ -f /var/lib/pacman/local ]; then
        packages=$(find /var/lib/pacman/local -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    fi
    
    echo "$packages"
}

get_network_info() {
    local network=""
    if [ -f /proc/net/route ]; then
        network=$(awk '$2 == "00000000" {print $1}' /proc/net/route | head -n1)
    fi
    
    if [ -n "$network" ]; then
        local ip_addr=""
        if [ -f /proc/net/fib_trie ]; then
            ip_addr=$(ip addr show "$network" 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1 | head -n1)
        fi
        echo "${network} (${ip_addr:-Unknown IP})"
    else
        echo "No connection"
    fi
}

get_load_average() {
    if [ -f /proc/loadavg ]; then
        cat /proc/loadavg | cut -d' ' -f1-3
    else
        echo "Unknown"
    fi
}

clear

OS=$(get_os_info)
KERNEL=$(get_kernel_info)
HOSTNAME=$(get_hostname)
UPTIME=$(get_uptime)
SHELL=$(get_shell_info)
RESOLUTION=$(get_resolution)
DE=$(get_desktop_environment)
CPU=$(get_cpu_info)
CPU_USAGE=$(get_cpu_usage)
CPU_TEMP=$(get_cpu_temp)
GPU=$(get_gpu_info)
MEMORY=$(get_memory_info)
DISK=$(get_disk_info)
BATTERY=$(get_battery_info)
LOCALE=$(get_locale_info)
PACKAGES=$(get_packages_info)
NETWORK=$(get_network_info)
LOAD_AVG=$(get_load_average)

LOGO_LINES=(
    "        ${ACCENT}░ ░░░░                            ░░░░░░${NC}"
    "        ${ACCENT}░░░░░░                            ░░░░░░${NC}"
    "        ${ACCENT}░░░▓▓░░░░   ░░░░░░░░░░░░░░░░░  ░░░░▒▒░░${NC}"
    "         ${ACCENT}░░▓▓▓▓▓▓░░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░░▒▒▒▒▒▒░░${NC}"
    "           ${ACCENT}░▓▓▓▓▓▓▓▓▓░░░▒▒▒▒▒▒▒▒░░░▒▒▒▒▒▒▒▒▒▒░${NC}"
    "           ${ACCENT}░░▓▓▓▓▓▓▓▓▓▓▒░░▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒░░${NC}"
    "        ${ACCENT}░░░▒▓▓░░░░░░░░░▓▓░░▒▒░░▒▒░░░░░░░░░▒▒░░░░${NC}"
    "        ${ACCENT}░░▓▓▓░   ░██░░░░▓▓░░░▒▒▒░░▒░██░░░░░▒▒▒░░${NC}"
    "        ${ACCENT}░░▓▓░░ ░░██░░░█░░▓▓░░▒▒░░▒░░░██░  ░░▒▒░${NC}"
    "        ${ACCENT}░░▓▓░  ░░███▓█▓░░▓▓░░▒▒░░██▓███░░ ░░▒▒░░${NC}"
    "        ${ACCENT}░░▓▓░░   ░░█▓░░░░▓▓░░▒▒░░░░▓█░░   ░░▒▒░░${NC}"
    "         ${ACCENT}░░▓▓░░░░  ░░░░▒▓▓░░░░▒▒░░░░░░  ░░░░▒▒░░░${NC}"
    "        ${ACCENT}░░░░▓▓▓▓░░░░░▓▓▓▒░░▒▒░░▒▒▒▒░░░░░▒▒▒▒░░░░${NC}"
    "           ${ACCENT}░░░░▓▓▓▓▓▓▒░░░░░▒▒░░░░░▒▒▒▒▒▒▒░░░░${NC}"
    "           ${ACCENT}░░░▒▒░░░░░▒▒▒▒▒░░░░▒▒▒▒▒░░░░░▒▒░░░${NC}"
    "           ${ACCENT}░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░${NC}"
    "              ${ACCENT}░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░${NC}"
    "                 ${ACCENT}░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░${NC}"
    "                 ${ACCENT}░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░${NC}"
    "                   ${ACCENT}░░░░▒▒▒▒▒▒▒▒▒▒░░░░${NC}"
    "                      ${ACCENT}░░░▒▒▒▒▒▒░░░${NC}"
    "                      ${ACCENT}░░░░░▒▒░░░░░${NC}"
    "                         ${ACCENT}░░░░░░${NC}"
)

INFO_LINES=(
    "${PRIMARY}$(whoami)${SECONDARY}@${ACCENT}${HOSTNAME}${NC}"
    "${BORDER}$(printf '%.0s─' {1..45})${NC}"
    "${ACCENT}󰍹 ${PRIMARY}System${NC}"
    "${ACCENT}├─ ${PRIMARY}OS${NC}         ${SECONDARY}${OS}${NC}"
    "${ACCENT}├─ ${PRIMARY}Kernel${NC}     ${SECONDARY}${KERNEL}${NC}"
    "${ACCENT}├─ ${PRIMARY}Uptime${NC}     ${SECONDARY}${UPTIME}${NC}"
    "${ACCENT}├─ ${PRIMARY}Packages${NC}   ${SECONDARY}${PACKAGES}${NC}"
    "${ACCENT}└─ ${PRIMARY}Shell${NC}      ${SECONDARY}${SHELL}${NC}"
    ""
    "${ACCENT}󰍹 ${PRIMARY}Hardware${NC}"
    "${ACCENT}├─ ${PRIMARY}CPU${NC}        ${SECONDARY}${CPU}${NC}"
    "${ACCENT}├─ ${PRIMARY}GPU${NC}        ${SECONDARY}${GPU}${NC}"
    "${ACCENT}├─ ${PRIMARY}Memory${NC}     ${SECONDARY}${MEMORY}${NC}"
    "${ACCENT}└─ ${PRIMARY}Disk${NC}       ${SECONDARY}${DISK}${NC}"
    ""
    "${ACCENT}󰍹 ${PRIMARY}Performance${NC}"
    "${ACCENT}├─ ${PRIMARY}CPU Usage${NC}  ${SECONDARY}${CPU_USAGE}%${NC}"
    "${ACCENT}├─ ${PRIMARY}CPU Temp${NC}   ${SECONDARY}${CPU_TEMP}${NC}"
    "${ACCENT}└─ ${PRIMARY}Load Avg${NC}   ${SECONDARY}${LOAD_AVG}${NC}"
    ""
    "${ACCENT}󰍹 ${PRIMARY}Environment${NC}"
    "${ACCENT}├─ ${PRIMARY}DE/WM${NC}      ${SECONDARY}${DE}${NC}"
    "${ACCENT}├─ ${PRIMARY}Resolution${NC} ${SECONDARY}${RESOLUTION}${NC}"
    "${ACCENT}├─ ${PRIMARY}Locale${NC}     ${SECONDARY}${LOCALE}${NC}"
    "${ACCENT}└─ ${PRIMARY}Network${NC}    ${SECONDARY}${NETWORK}${NC}"
)

if [ -n "$BATTERY" ]; then
    INFO_LINES+=("")
    INFO_LINES+=("${ACCENT}󰁹 ${PRIMARY}Battery${NC}    ${SECONDARY}${BATTERY}${NC}")
fi

INFO_LINES+=("")
PALETTE="${SECONDARY}Colors: "
colors=("$BLACK" "$RED" "$GREEN" "$YELLOW" "$BLUE" "$PURPLE" "$CYAN" "$WHITE")
for color in "${colors[@]}"; do
    PALETTE+="${color}███${NC}"
done
INFO_LINES+=("$PALETTE")

MAX_LOGO_WIDTH=0
for line in "${LOGO_LINES[@]}"; do
    current_width=$(get_string_length "$line")
    if [ $current_width -gt $MAX_LOGO_WIDTH ]; then
        MAX_LOGO_WIDTH=$current_width
    fi
done

echo
max_lines=${#LOGO_LINES[@]}
info_count=${#INFO_LINES[@]}

if [ $info_count -gt $max_lines ]; then
    max_lines=$info_count
fi

for ((i=0; i<max_lines; i++)); do
    if [ $i -lt ${#LOGO_LINES[@]} ]; then
        echo -ne "${LOGO_LINES[$i]}"
        current_width=$(get_string_length "${LOGO_LINES[$i]}")
        spaces_needed=$((MAX_LOGO_WIDTH - current_width + 4))
        printf '%*s' $spaces_needed ''
    else
        printf '%*s' $((MAX_LOGO_WIDTH + 4)) ''
    fi
    
    if [ $i -lt ${#INFO_LINES[@]} ]; then
        echo -e "${INFO_LINES[$i]}"
    else
        echo
    fi
done

echo
echo

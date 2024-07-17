#!/bin/bash

# ANSI color codes for colored output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Setup environment variable for Anaconda version. Change this to the desired version
ANACONDA_VERSION='2024.02-1'

# Function to determine the OS and package manager
detect_os() {
    echo -e "${BLUE}Detecting operating system...${RESET}"
    if [ "$(uname)" == "Darwin" ]; then
        OS="macos"
        PKG_MANAGER="brew"
        echo -e "${GREEN}macOS detected.${RESET}"
    elif [ -f /etc/os-release ]; then
        . /etc/os-release
        case $ID in
            debian|ubuntu)
                OS="ubuntu"
                PKG_MANAGER="apt-get"
                echo -e "${GREEN}Ubuntu/Debian detected.${RESET}"
                ;;
            fedora|centos|rhel|amzn)
                OS="fedora"
                PKG_MANAGER="yum"
                echo -e "${GREEN}Fedora/RHEL/CentOS/AMZN detected.${RESET}"
                ;;
            *)
                echo -e "${RED}Unsupported operating system.${RESET}"
                exit 1
                ;;
        esac
    else
        echo -e "${RED}Unable to detect operating system.${RESET}"
        exit 1
    fi
}

# Function to install necessary libraries before installing Conda
install_conda_dependencies() {
    echo -e "${YELLOW}Installing dependencies for Conda...${RESET}"
    if [ "$OS" == "ubuntu" ]; then
        sudo apt-get update && sudo apt-get install -y libgl1-mesa-glx libegl1-mesa libxrandr2 libxss1 libxcursor1 libxcomposite1 libasound2 libxi6 libxtst6
    elif [ "$OS" == "fedora" ]; then
        sudo yum install -y libXcomposite libXcursor libXi libXtst libXrandr alsa-lib mesa-libEGL libXdamage mesa-libGL libXScrnSaver
    fi
}

# Function to install Conda
install_conda() {
    echo "Installing Linux dependencies for Conda..."
    install_conda_dependencies || return 1

    # Use actual user's home directory, not root's
    local actual_user_home=$(eval echo ~$SUDO_USER)

    # Check if the Anaconda install directory already exists
    if [ -d "${actual_user_home}/anaconda3" ]; then
        echo -e "${RED}Existing Anaconda installation found. Removing...${RESET}"
        rm -rf "${actual_user_home}/anaconda3" || return 1
    fi

    echo -e "${YELLOW}Downloading Anaconda installer...${RESET}"
    local conda_installer="Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
    curl -O https://repo.anaconda.com/archive/$conda_installer || return 1

    echo -e "${YELLOW}Changing mode for bash execution Anaconda...${RESET}"
    chmod +x $conda_installer || return 1

    echo -e "${YELLOW}Installing Anaconda...${RESET}"
    # Use the -b (batch) option to accept the default installation options
    bash $conda_installer -b -p "${actual_user_home}/anaconda3" || return 1

    echo -e "${GREEN}Initializing Anaconda...${RESET}"
    source "${actual_user_home}/anaconda3/bin/activate"
    conda init || return 1

    echo -e "${YELLOW}Setting auto_activate_base configuration...${RESET}"
    conda config --set auto_activate_base true || return 1
    echo -e "${GREEN}Anaconda installation complete. Thank you for installing Anaconda3!${RESET}"

    # Reload .bashrc to apply changes
    source "${actual_user_home}/.bashrc" || return 1
}


# Initialize the script
detect_os
install_conda
echo "Conda version: $(conda --version)"
source ~/.bashrc

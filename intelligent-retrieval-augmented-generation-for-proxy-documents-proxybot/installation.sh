#!/bin/bash

# ANSI color codes for colored output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Set Anaconda version, default if not set
ANACONDA_VERSION=${ANACONDA_VERSION:-2024.02-1}

# # Ensuring Python and curl are installed
# if ! command -v python3 &> /dev/null || ! command -v curl &> /dev/null; then
#     echo "Python3 or curl is not installed. Installing them now..."
#     sudo apt-get update
#     sudo apt-get install -y curl python3  # Adjust as necessary for your package manager
# fi

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
            fedora|centos|rhel)
                OS="fedora"
                PKG_MANAGER="yum"
                echo -e "${GREEN}Fedora/RHEL/CentOS detected.${RESET}"
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

# Setup environment variable for Anaconda version
ANACONDA_VERSION="2024.02-1"  # Change this to the desired version

# Function to install Conda
# install_conda() {
#     # Check if the Anaconda install directory already exists
#     if [ -d "$HOME/anaconda3" ]; then
#         echo -e "${RED}Existing Anaconda installation found. Removing...${RESET}"
#         rm -rf "$HOME/anaconda3"
#     fi

#     echo -e "${YELLOW}Downloading Anaconda installer...${RESET}"
#     local conda_installer="Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
#     curl -O https://repo.anaconda.com/archive/$conda_installer

#     echo -e "${YELLOW}Installing Anaconda...${RESET}"
#     bash $conda_installer -b -p $HOME/anaconda3

#     echo -e "${GREEN}Initializing Anaconda...${RESET}"
#     source $HOME/anaconda3/bin/activate
#     conda init

#     echo -e "${YELLOW}Setting auto_activate_base configuration...${RESET}"
#     conda config --set auto_activate_base true
#     echo -e "${GREEN}Anaconda installation complete. Thank you for installing Anaconda3!${RESET}"

#     # Reload .bashrc to apply changes
#     source ~/.bashrc
# }

# # Function to install Conda
# install_conda() {
#     # Check if the Anaconda install directory already exists
#     local conda_dir="$HOME/anaconda3"
#     if [ -d "$conda_dir" ]; then
#         echo -e "${RED}Existing Anaconda installation found. Removing...${RESET}"
#         rm -rf "$conda_dir"
#     fi

#     echo -e "${YELLOW}Downloading Anaconda installer...${RESET}"
#     local conda_installer="Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
#     curl -O https://repo.anaconda.com/archive/$conda_installer

#     echo -e "${YELLOW}Installing Anaconda...${RESET}"
#     bash $conda_installer -b -p "$conda_dir"

#     echo -e "${GREEN}Initializing Anaconda...${RESET}"
#     source "$conda_dir/bin/activate"
#     conda init

#     echo -e "${YELLOW}Setting auto_activate_base configuration...${RESET}"
#     conda config --set auto_activate_base true
#     echo -e "${GREEN}Anaconda installation complete. Thank you for installing Anaconda3!${RESET}"

#     # Reload .bashrc to apply changes
#     source ~/.bashrc
# }

# Function to install Conda
install_conda() {
    echo "Installing Linux dependencies for Conda..."
    sudo apt-get update && sudo apt-get install -y \
        libgl1-mesa-glx libegl1-mesa libxrandr2 libxss1 \
        libxcursor1 libxcomposite1 libasound2 libxi6 libxtst6

    # Use actual user's home directory, not root's
    local actual_user_home=$(eval echo ~$SUDO_USER)

    # Check if the Anaconda install directory already exists
    if [ -d "${actual_user_home}/anaconda3" ]; then
        echo -e "${RED}Existing Anaconda installation found. Removing...${RESET}"
        rm -rf "${actual_user_home}/anaconda3"
    fi

    echo -e "${YELLOW}Downloading Anaconda installer...${RESET}"
    local conda_installer="Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
    curl -O https://repo.anaconda.com/archive/$conda_installer

    echo -e "${YELLOW}Installing Anaconda...${RESET}"
    bash $conda_installer -b -p "${actual_user_home}/anaconda3"

    echo -e "${GREEN}Initializing Anaconda...${RESET}"
    source "${actual_user_home}/anaconda3/bin/activate"
    conda init

    echo -e "${YELLOW}Setting auto_activate_base configuration...${RESET}"
    conda config --set auto_activate_base true
    echo -e "${GREEN}Anaconda installation complete. Thank you for installing Anaconda3!${RESET}"

    # Reload .bashrc to apply changes
    source "${actual_user_home}/.bashrc"
}

# Function to install Poetry
install_poetry() {
    echo -e "${YELLOW}Installing Poetry...${RESET}"
    curl -sSL https://install.python-poetry.org | python -

    # Add Poetry to PATH
    POETRY_HOME="$HOME/.local/bin"
    export PATH="$POETRY_HOME:$PATH"
    echo "export PATH=\"$POETRY_HOME:\$PATH\"" >> $HOME/.bashrc
    source $HOME/.bashrc

    echo -e "${GREEN}Poetry has been configured and is ready to use.${RESET}"
}

# Function to install and configure Conda
install_and_configure_conda() {
    install_conda_dependencies
    echo -e "${YELLOW}Installing Conda version $ANACONDA_VERSION...${RESET}"
    wget "https://repo.anaconda.com/archive/Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh" -O ~/Downloads/anaconda_installer.sh
    bash ~/Downloads/anaconda_installer.sh -b -p $HOME/anaconda
    source $HOME/anaconda/bin/activate
    conda init
    echo -e "${GREEN}Conda installed and initialized.${RESET}"
}

# Ensure the directory exists and navigate to it
# mkdir -p $HOME/Downloads
# cd $HOME/Downloads

# Function to download and install Anaconda
# Function to download and install Anaconda
download_and_install_conda() {
    echo -e "${YELLOW}Downloading Anaconda version $ANACONDA_VERSION...${RESET}"
    local url="https://repo.anaconda.com/archive/Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
    local installer="anaconda_installer.sh"
    local checksum="your_expected_checksum_here"

    # Ensure the directory exists and navigate to it
    mkdir -p $HOME/Downloads
    cd $HOME/Downloads

    # Download the Anaconda installer
    wget "$url" -O "$installer"

    # Verify the checksum
    echo "${checksum}  ${installer}" | sha256sum -c -
    if [ $? -ne 0 ]; then
        echo -e "${RED}Checksum verification failed. The installer may be corrupted.${RESET}"
        exit 1
    fi

    # Install Anaconda
    echo -e "${YELLOW}Installing Conda...${RESET}"
    bash "$installer" -b -p $HOME/anaconda || {
        echo -e "${RED}Anaconda installation failed.${RESET}"
        exit 1
    }

    # Initialize Conda
    if [ -f "$HOME/anaconda/bin/activate" ]; then
        source $HOME/anaconda/bin/activate
        conda init
        echo -e "${GREEN}Conda installed and initialized.${RESET}"
    else
        echo -e "${RED}Conda installation script did not complete successfully.${RESET}"
        exit 1
    fi
}

download_and_install_conda__() {
    echo -e "${YELLOW}Downloading Anaconda version $ANACONDA_VERSION...${RESET}"
    local url="https://repo.anaconda.com/archive/Anaconda3-${ANACONDA_VERSION}-Linux-x86_64.sh"
    local installer="anaconda_installer.sh"

    # Use wget to download the Anaconda installer
    if ! wget "$url" -O "$installer"; then
        echo -e "${RED}Failed to download Anaconda installer. Please check the version and network connection.${RESET}"
        exit 1
    fi

    # Ensure the installer is executable
    chmod +x "$installer"

    # Install Anaconda
    echo -e "${YELLOW}Installing Conda...${RESET}"
    ./"$installer" -b -p $HOME/anaconda

    # Initialize Conda
    source $HOME/anaconda/bin/activate
    conda init
    echo -e "${GREEN}Conda installed and initialized.${RESET}"
}

# Install Poetry function
install_poetry() {
    echo "Installing Poetry..."

    # Install Poetry using Python3
    curl -sSL https://install.python-poetry.org | python3 - || {
        echo "Failed to install Poetry."
        return 1  # Return with error
    }

    # Add Poetry to PATH and apply changes immediately
    POETRY_HOME="$HOME/.local/bin"
    export PATH="$POETRY_HOME:$PATH"
    echo "export PATH=\"$POETRY_HOME:\$PATH\"" >> $HOME/.bashrc
    source $HOME/.bashrc

    echo "Poetry has been configured and is ready to use."
}

# Function to configure Poetry to ensure it's available
configure_poetry() {
    echo -e "${BLUE}Configuring Poetry...${RESET}"
    POETRY_HOME="$HOME/.local/bin"
    mkdir -p $POETRY_HOME
    export PATH="$POETRY_HOME:$PATH"
    echo "export PATH=\"$POETRY_HOME:\$PATH\"" >> $HOME/.bashrc
    curl -sSL https://install.python-poetry.org | python -
    source $HOME/.bashrc
    echo -e "${GREEN}Poetry configured and ready to use.${RESET}"
}

# Unified function to install and configure Poetry
install_and_configure_poetry() {
    echo -e "${BLUE}Installing and configuring Poetry...${RESET}"

    # Use actual user's home directory, not root's
    local actual_user_home=$(eval echo ~$SUDO_USER)

    # Ensure the local bin directory exists
    POETRY_HOME="${actual_user_home}/.local/bin"
    mkdir -p $POETRY_HOME
    export PATH="$POETRY_HOME:$PATH"
    echo "export PATH=\"$POETRY_HOME:\$PATH\"" >> $HOME/.bashrc

    # Install Poetry using Python3
    curl -sSL https://install.python-poetry.org | python3 - || {
        echo -e "${RED}Failed to install Poetry.${RESET}"
        return 1  # Return with error
    }

    # Source .bashrc to apply PATH changes immediately
    source $HOME/.bashrc

    # export PATH="/home/iam_dayo_john/.local/bin:$PATH"
    export PATH="$POETRY_HOME:$PATH"
    echo -e "${GREEN}Poetry has been installed and configured. It is ready to use.${RESET}"
}


# Function to install Docker and Docker Compose
install_docker() {
    echo -e "${BLUE}Installing Docker...${RESET}"
    if [ "$OS" == "ubuntu" ]; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        echo $USER
        sudo usermod -aG docker $USER
        sudo systemctl start docker
        sudo systemctl enable docker
    elif [ "$OS" == "fedora" ]; then
        sudo dnf -y install dnf-plugins-core
        sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        sudo dnf -y install docker-ce docker-ce-cli containerd.io
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    echo -e "${GREEN}Docker installed and running.${RESET}"

    # Install Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed.${RESET}"
}

# Function to set Python as the default Python3
alias_python() {
    echo "alias python=python3" >> $HOME/.bashrc
    source $HOME/.bashrc
}

# Install Git
echo -e "${BLUE}Installing Git...${RESET}"
if [ "$OS" == "ubuntu" ] || [ "$OS" == "fedora" ]; then
    sudo $PKG_MANAGER install -y git
    echo -e "${GREEN}Git installed.${RESET}"
fi

# Initialize the script
detect_os
install_docker
alias_python
# install_and_configure_conda
# download_and_install_conda
# configure_poetry
# Call the install Poetry function
# install_poetry
# Call the Poetry installation and configuration function
## install_and_configure_poetry
# Call functions to install Conda and Poetry
install_conda
# install_poetry

ls -l /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock
sudo usermod -aG docker $USER
newgrp docker
echo "Testing Docker installation by running the 'hello-world' container..."
docker run hello-world
echo -e "${GREEN}Docker is configured and tested successfully.${RESET}"
# Testing installations
echo "Testing installations:"
echo "Git version: $(git --version)"
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo "Conda version: $(conda --version)"
echo "Poetry version: $(poetry --version)"

source ~/.bashrc

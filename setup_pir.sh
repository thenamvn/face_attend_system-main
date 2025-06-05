#!/bin/bash
# Script tự động cài đặt và khởi động pigpiod cho Raspberry Pi

set -e

echo "Updating package lists..."
sudo apt update

echo "Installing pigpio and python3-pigpio packages..."
sudo apt install -y pigpio python3-pigpio

echo "Enabling pigpiod daemon to start at boot..."
sudo systemctl enable pigpiod

echo "Starting pigpiod daemon now..."
sudo systemctl start pigpiod

echo "Checking pigpiod daemon status:"
sudo systemctl status pigpiod --no-pager

echo "Setup complete! You should now have pigpiod running."

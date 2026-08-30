#!/bin/bash
# 一键编译全部 demos（MinGW）。前提：先跑过 build_libuvc.sh。
# 依赖 DLL 已由 phase1 演示拷贝进 demos/（libusb-1.0.dll、libwinpthread-1.dll）。
# 在 Ubuntu VM 等 Linux 环境下，等价命令：
#   gcc -o 程序名 程序名.c -luvc -lusb-1.0 -lpthread

set -e
cd "$(dirname "$0")/../demos"

UVC_INC="../libuvc/include:../libuvc/build/include"
UVC_LIB="../libuvc/build"
USB_LIB="../third_party/libusb-dist/mingw64/lib"

for src in phase*.c; do
  exe="${src%.c}.exe"
  echo "== 编译 $src -> $exe"
  gcc -I"${UVC_INC%%:*}" -I"${UVC_INC##*:}" "$src" \
      -L"$UVC_LIB" -luvc \
      -L"$USB_LIB" -lusb-1.0 \
      -lwinpthread -o "$exe"
done

echo "全部完成。可运行："
echo "  ./phase2_device_list.exe   （无需摄像头）"
echo "  ./phase10_convert.exe      （无需摄像头）"
echo "  ./phase3_open_close.exe    （需先解决 D1：USBDK/外置摄像头）"

#!/bin/bash
# 一键搭建 libusb + libuvc 编译环境（MinGW）
# 背景：github.com 不通；libusb 新版已无 CMake 构建系统；
#       libuvc 的 FindLibUSB.cmake 在 MinGW 上直接 return()。
# 方案：libusb 用清华 MSYS2 镜像预编译包 + bsdtar 解压；
#       libuvc 用 CMAKE_PROJECT_INCLUDE 预定义 LibUSB::LibUSB 目标。
# 详见 findings.md「编译环境搭建实录」。

set -e
cd "$(dirname "$0")/.."   # 回到 LearnUVC/

THIRD=third_party
DIST=$THIRD/libusb-dist
PKG_URL="https://mirrors.tuna.tsinghua.edu.cn/msys2/mingw/mingw64/mingw-w64-x86_64-libusb-1.0.27-1-any.pkg.tar.zst"

echo "== [1/3] 获取预编译 libusb（清华 MSYS2 镜像）=="
mkdir -p "$THIRD"
if [ ! -f "$DIST/mingw64/bin/libusb-1.0.dll" ]; then
    curl -s --max-time 120 -o "$THIRD/libusb-mingw.pkg.tar.zst" "$PKG_URL"
    mkdir -p "$DIST"
    /c/Windows/System32/tar.exe -xf "$THIRD/libusb-mingw.pkg.tar.zst" -C "$DIST"
    echo "libusb 就绪: $DIST"
else
    echo "libusb 已存在，跳过下载"
fi

echo "== [2/3] 配置 libuvc（MinGW Makefiles，静态库）=="
mkdir -p libuvc/build
cd libuvc/build
cmake -G "MinGW Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_BUILD_TARGET=Static \
    -DBUILD_EXAMPLE=ON \
    -DLibUVC_STATIC=ON \
    -DCMAKE_THREAD_LIBS_INIT=-lwinpthread \
    -DCMAKE_PROJECT_INCLUDE="D:/CC/personal-lr-notes/CCNotes/LearnUVC/scripts/predefine-libusb-target.cmake" \
    ..

echo "== [3/3] 编译 =="
mingw32-make -j4
echo "完成: libuvc.a + example.exe"
echo "demo 链接命令参考 demos/phase1_init.c 头注释"

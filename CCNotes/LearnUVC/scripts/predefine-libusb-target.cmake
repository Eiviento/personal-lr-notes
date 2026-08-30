# libuvc 的 cmake/FindLibUSB.cmake 在 MinGW 上有坑：
#   if (MSVC OR MINGW) return()
# 即 MinGW 下 find_package(LibUSB) 什么都不做，LibUSB::LibUSB 目标不存在，
# 导致 target_link_libraries 报错。
#
# 解决办法：通过 CMAKE_PROJECT_INCLUDE 在 project() 之后、
# find_package(LibUSB) 之前，预先定义好 LibUSB::LibUSB 导入目标。
# libusb 本身不用源码编译，直接用清华 MSYS2 镜像的预编译 MinGW 包：
#   third_party/libusb-dist/mingw64/{bin,include,lib}
#
# 用法：
#   cmake -G "MinGW Makefiles" \
#     -DCMAKE_PROJECT_INCLUDE=D:/CC/personal-lr-notes/CCNotes/LearnUVC/scripts/predefine-libusb-target.cmake \
#     .. && mingw32-make

if(NOT TARGET LibUSB::LibUSB)
  set(_LIBUSB_DIST "D:/CC/personal-lr-notes/CCNotes/LearnUVC/third_party/libusb-dist/mingw64")
  add_library(LibUSB::LibUSB UNKNOWN IMPORTED)
  set_target_properties(LibUSB::LibUSB PROPERTIES
    IMPORTED_LOCATION "${_LIBUSB_DIST}/lib/libusb-1.0.dll.a"
    INTERFACE_INCLUDE_DIRECTORIES "${_LIBUSB_DIST}/include/libusb-1.0"
  )
  message(STATUS "Predefined LibUSB::LibUSB -> ${_LIBUSB_DIST}")
endif()

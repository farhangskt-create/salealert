# Sale Alert Native Scraper Engine CMake Build Configuration
cmake_minimum_required(VERSION 3.22.1)
project("salealert")

# Enforce 16 KB page alignment for Android 15/16 compatibility (Google Play mandatory requirement)
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-z,max-page-size=16384")

# Declare native scraper library
add_library(
    native-scraper
    SHARED
    native-lib.cpp
)

# Find Android logging library
find_library(log-lib log)

# Link target library with log library
target_link_libraries(
    native-scraper
    ${log-lib}
)

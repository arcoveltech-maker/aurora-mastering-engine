cmake_minimum_required(VERSION 3.20)
project(aurora-dsp VERSION 5.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(AURORA_BUILD_WASM "Build WASM with Emscripten" OFF)
option(AURORA_BUILD_TESTS "Build tests" ON)

set(AURORA_DSP_SOURCES
  src/biquad.cpp
  src/lufs.cpp
  src/true_peak.cpp
  src/crossover.cpp
  src/saturation.cpp
  src/linear_phase_eq.cpp
  src/ms_processing.cpp
  src/limiter.cpp
  src/dither.cpp
  src/engine.cpp
)

if(AURORA_BUILD_WASM)
  set(CMAKE_EXECUTABLE_SUFFIX ".js")
  add_compile_options(-O3 -flto -msimd128)
  add_executable(aurora_dsp ${AURORA_DSP_SOURCES} src/bindings.cpp)
  target_include_directories(aurora_dsp PRIVATE ${CMAKE_SOURCE_DIR}/include)
  target_compile_definitions(aurora_dsp PRIVATE __EMSCRIPTEN__=1)
  set_target_properties(aurora_dsp PROPERTIES
    LINK_FLAGS "-s MODULARIZE=1 -s EXPORT_NAME=AuroraDSP -s ALLOW_MEMORY_GROWTH=1 \
                -s EXPORTED_RUNTIME_METHODS=['ccall','cwrap'] \
                -s ENVIRONMENT=web --bind -flto"
  )
else()
  add_library(auroradsp STATIC ${AURORA_DSP_SOURCES})
  target_include_directories(auroradsp PUBLIC ${CMAKE_SOURCE_DIR}/include)

  if(AURORA_BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
      googletest
      URL https://github.com/google/googletest/archive/v1.14.0.zip
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    enable_testing()

    add_executable(test_runner
      tests/test_main.cpp
      tests/test_lufs.cpp
      tests/test_true_peak.cpp
      tests/test_multiband.cpp
      tests/test_saturation.cpp
      tests/test_limiter.cpp
      tests/test_acceptance.cpp
    )
    target_link_libraries(test_runner PRIVATE auroradsp GTest::gtest_main)
    include(GoogleTest)
    gtest_discover_tests(test_runner)
  endif()
endif()

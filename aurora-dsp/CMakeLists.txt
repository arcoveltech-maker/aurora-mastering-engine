cmake_minimum_required(VERSION 3.20)
project(aurora-dsp VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)

option(AURORA_BUILD_WASM "Build WASM with Emscripten" OFF)
option(AURORA_BUILD_TESTS "Build tests" ON)

if(AURORA_BUILD_WASM)
  # Emscripten: KissFFT, flags per blueprint
  set(CMAKE_EXECUTABLE_SUFFIX ".js")
  add_compile_options(-O3 -flto -msimd128)
  add_executable(aurora_dsp
    src/bindings.cpp
    src/biquad.cpp
    src/lufs.cpp
    src/true_peak.cpp
    src/engine.cpp
    src/multiband_compressor.cpp
    src/dynamic_eq.cpp
    src/transient_designer.cpp
    src/riaa.cpp
    src/analog_residual.cpp
    src/psychoacoustic.cpp
    src/spatial_renderer.cpp
    src/binaural.cpp
  )
  target_include_directories(aurora_dsp PRIVATE ${CMAKE_SOURCE_DIR}/include)
  target_compile_definitions(aurora_dsp PRIVATE __EMSCRIPTEN__=1)
  target_link_options(aurora_dsp PRIVATE
    "SHELL:-s EXPORTED_FUNCTIONS=[_aurora_create,_aurora_destroy,_aurora_process,_aurora_get_version]"
    "SHELL:-s EXPORTED_RUNTIME_METHODS=[cwrap,ccall,getValue,setValue]"
    "SHELL:-s ALLOW_MEMORY_GROWTH=1"
    "SHELL:-s WASM=1"
    "SHELL:-s MODULARIZE=1"
    "SHELL:-s EXPORT_NAME=AuroraDSP"
  )
else()
  # Native: build library + tests
  add_library(auroradsp STATIC
    src/biquad.cpp
    src/lufs.cpp
    src/true_peak.cpp
    src/engine.cpp
    src/multiband_compressor.cpp
    src/dynamic_eq.cpp
    src/transient_designer.cpp
    src/riaa.cpp
    src/analog_residual.cpp
    src/psychoacoustic.cpp
    src/spatial_renderer.cpp
    src/binaural.cpp
  )
  target_include_directories(auroradsp PUBLIC ${CMAKE_SOURCE_DIR}/include)
  if(AURORA_BUILD_TESTS)
    enable_testing()
    add_executable(test_runner tests/test_main.cpp)
    target_link_libraries(test_runner PRIVATE auroradsp)
    add_test(NAME AuroraDSPTests COMMAND test_runner)
  endif()
endif()

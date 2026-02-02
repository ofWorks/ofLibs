# ofLibs / Librares for [ofWorks (openFrameworks fork)](https://github.com/dimitre/ofworks)
Building libraries for multiple platforms.<br>
You are welcome to jump in and help building and testing more libraries.<br>

## Core Libraries

| Library | vs | macos | linux64 | rpi-aarch64 | rpi-armv6l |
|---------|:--:|:-----:|:-------:|:-----------:|:----------:|
| freetype | ✓ | ✓ | ✓ | ✓ | ✓ |
| glew | ✓ | ✓ | ✓ | ✓ | ✓ |
| glfw | ✓ | ✓ | ✓ | ✓ | ✓ |
| glm | ✓ | ✓ | ✓ | ✓ | ✓ |
| json | ✓ | ✓ | ✓ | ✓ | ✓ |
| kissfft | — | — | ✓ | ✓ | ✓ |
| mango | ✓ | ✓ | ✓ | ✓ | ✓ |
| pugixml | ✓ | ✓ | ✓ | ✓ | ✓ |
| rtAudio | ✓ | ✓ | ✓ | ✓ | ✓ |
| tess2 | ✓ | ✓ | ✓ | ✓ | ✓ |
| uriparser | ✓ | ✓ | ✓ | ✓ | ✓ |
| utfcpp | ✓ | ✓ | ✓ | ✓ | ✓ |
| videoInput | ✓ | — | — | — | — |
| yaml-cpp | ✓ | ✓ | ✓ | ✓ | ✓ |
| zlib-ng | ✓ | ✓ | ✓ | ✓ | ✓ |

## Addon Libraries

| Library | vs | macos | linux64 | rpi-aarch64 | rpi-armv6l | Associated Addon |
|---------|:--:|:-----:|:-------:|:-----------:|:----------:|------------------|
| assimp | ✓ | ✓ | ✓ | ✓ | ✓ | ofxAssimp |
| cairo | ✓ | ✓ | ✓ | ✓ | ✓ | ofxCairo |
| libusb | ✓ | ✓ | ✓ | ✓ | ✓ | ofxKinect |
| opencv | ✓ | ✓ | ✓ | ✓ | ✓ | ofxOpenCv |
| pixman | ✓ | ✓ | ✓ | ✓ | ✓ | ofxCairo |

## Building
The github workflow actions automatically build the libraries individually when changes are made. You can grab them from the releases.
You can build the all libraries locally by running `./compile.sh`.
Or proceed manually by `cd libFolder` and or `./lib.sh`.

## ofCore
![title](https://github.com/dimitre/ofLibs/actions/workflows/freetype.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/glew.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/glfw.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/glm.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/json.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/kissfft.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/libusb.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/pugixml.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/rtAudio.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/tess2.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/uriparser.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/utfcpp.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/videoInput.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/zlib-ng.yml/badge.svg)

## ofCore ofWorks
![title](https://github.com/dimitre/ofLibs/actions/workflows/fmt.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/yaml-cpp.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/mango.yml/badge.svg)

## Addons Modern
![title](https://github.com/dimitre/ofLibs/actions/workflows/blend2d.yml/badge.svg)

## Addons
![title](https://github.com/dimitre/ofLibs/actions/workflows/assimp.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/cairo.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/opencv.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/pixman.yml/badge.svg)
<br><br>
Still missing ofxURL related libs, openssl, libcrypto

![title](https://github.com/dimitre/ofLibs/actions/workflows/openssl-curl.yml/badge.svg)

## Additional / Test (published with tag add)
![title](https://github.com/dimitre/ofLibs/actions/workflows/blend2d.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/poco.yml/badge.svg)
<!--![title](https://github.com/dimitre/ofLibs/actions/workflows/OpenImageIO.yml/badge.svg)-->

## Legacy Core
Brotli, libjpeg, libtiff, libpng, lzma builds correctly but moved aside from CI.<br>
FreeImage have some issues. Poco now builds again and it was moved to "Additional"
<!--[![title](https://github.com/dimitre/ofLibs/actions/workflows/brotli.yml/badge.svg)](https://github.com/dimitre/ofLibs/actions/workflows/brotli.yml)
[![title](https://github.com/dimitre/ofLibs/actions/workflows/FreeImage.yml/badge.svg)](https://github.com/dimitre/ofLibs/actions/workflows/FreeImage.yml)
![title](https://github.com/dimitre/ofLibs/actions/workflows/libjpeg.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/libtiff.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/libpng.yml/badge.svg)
![title](https://github.com/dimitre/ofLibs/actions/workflows/lzma.yml/badge.svg)-->


![Xcode 26](img.shields.io)

![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

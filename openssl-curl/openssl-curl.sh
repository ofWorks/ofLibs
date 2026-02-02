#!/bin/bash
set -e

if [[ "$PWD" == "/Users/d/src/ofLibs/openssl-curl" ]]; then
echo "Local developtment"
PLATFORM=macos
else
# todo
PLATFORM=macos
fi

if [[ -z "${PLATFORM}" ]]; then
	echo "Error: This script requires a PLATFORM to run correctly ! Aborting."
	exit 0;
fi

cd "$(dirname "$0")"
cd Build-OpenSSL-cURL
# ./build.sh -o 3.0.15 -c 8.14.1 -d -i 11.0 -a 11.0
# ./build.sh -o 3.5.2 -c 8.15.0 -d -i 10.15 -a 11.0
./build.sh -o 3.5.2 -c 8.15.0 -d -i 10.15 -a -1

# mkdir dist

echo "[Packaging]"
echo "Gathering curl files..."
cd ..
mkdir -p curl
cd curl
cp -r ../Build-OpenSSL-cURL/curl/include .
cp -r ../Build-OpenSSL-cURL/curl/lib .
cp ../Build-OpenSSL-cURL/curl/curl*/COPYING .
echo "Copying libraries to lib/${PLATFORM}..."
mkdir -p lib/${PLATFORM}
mv lib/*.a lib/${PLATFORM}
echo "Compressing Release : ofLibs_curl_${PLATFORM}.zip"
zip -r ../ofLibs_curl_${PLATFORM}.zip lib include
cd ..

echo "Gathering openssl files..."
mkdir -p openssl
cd openssl
cp -r ../Build-OpenSSL-cURL/openssl/Mac/include .
cp -r ../Build-OpenSSL-cURL/openssl/Mac/lib .

# ls -alFR ../Build-OpenSSL-cURL/openssl/
# tree -h

# cp ../Build-OpenSSL-cURL/openssl/openssl*/LICENSE.* .
# exit 1

echo "Copying libraries to lib/${PLATFORM}..."
mkdir -p lib/${PLATFORM}
mv lib/*.a lib/${PLATFORM}

echo "Compressing Release : ofLibs_openssl_${PLATFORM}.zip"
zip -r ../ofLibs_openssl_${PLATFORM}.zip lib include
cd ..

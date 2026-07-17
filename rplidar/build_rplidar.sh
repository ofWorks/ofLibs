#!/bin/bash
# Builds a universal librplidar_sdk.a plus a staged include/ from the
# chalet-fetched dimitre/rplidar_sdk checkout (branch braid: upstream
# Slamtec SDK + capsule sync-bit, __APPLE__ macro, and RPM payload fixes).
# Invoked by the chalet script target with the checkout path as $1.
set -eu
export SDKROOT="${SDKROOT:-$(xcrun --show-sdk-path)}"
ROOT="$(cd "$1" && pwd)"
SRC="$ROOT/sdk"
STAGE="$ROOT/stage"

FILES=(
	src/sl_lidar_driver.cpp
	src/sl_crc.cpp
	src/sl_serial_channel.cpp
	src/sl_tcp_channel.cpp
	src/sl_udp_channel.cpp
	src/sl_lidarprotocol_codec.cpp
	src/sl_async_transceiver.cpp
	src/hal/thread.cpp
	src/dataunpacker/dataunpacker.cpp
	src/dataunpacker/unpacker/handler_normalnode.cpp
	src/dataunpacker/unpacker/handler_capsules.cpp
	src/dataunpacker/unpacker/handler_hqnode.cpp
	src/arch/macOS/net_serial.cpp
	src/arch/macOS/net_socket.cpp
	src/arch/macOS/timer.cpp
)

rm -rf "$STAGE"
mkdir -p "$STAGE/lib" "$STAGE/include"
cd "$SRC"

THIN=()
for ARCH in arm64 x86_64; do
	OBJ=$(mktemp -d)
	for f in "${FILES[@]}"; do
		echo "cc [$ARCH] $f"
		clang++ -std=c++17 -O2 -arch "$ARCH" -mmacosx-version-min=11.0 \
			-Iinclude -Isrc -w -c "$f" -o "$OBJ/$(basename "$f" .cpp).o"
	done
	ar rcs "$OBJ/librplidar_sdk.a" "$OBJ"/*.o
	THIN+=("$OBJ/librplidar_sdk.a")
done
lipo -create "${THIN[@]}" -output "$STAGE/lib/librplidar_sdk.a"
cp include/*.h "$STAGE/include/"
echo "Built: $STAGE/lib/librplidar_sdk.a"

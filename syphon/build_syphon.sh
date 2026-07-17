#!/bin/bash
# Builds Syphon.framework from the chalet-fetched Syphon-Framework checkout.
# Invoked by the chalet script target with the checkout path as $1.
# Universal (arm64 + x86_64), deployment target matching the other ofLibs.
# Xcode 26 ships the Metal shader compiler as a separate ~2 GB component;
# without it CompileMetalFile fails with "cannot execute tool 'metal'".
# Fetch it if absent (CI runners come bare).
set -eu
if ! xcrun --find metal &>/dev/null; then
	echo "Metal toolchain missing — downloading (~2 GB)"
	xcodebuild -downloadComponent MetalToolchain
fi
SRC="$1"
cd "$SRC"
xcodebuild -project Syphon.xcodeproj -target Syphon -configuration Release \
	ONLY_ACTIVE_ARCH=NO ARCHS="arm64 x86_64" MACOSX_DEPLOYMENT_TARGET=11.0 \
	build
echo "Built: $SRC/build/Release/Syphon.framework"

#!/bin/bash
cd "$(dirname "$0")"
set -eu

# Utility to compile libraries locally (osx 10.15)

COLOR='\033[0;32m'
COLOR2='\033[0;34m'
COLOR3='\033[0;95m'
NC='\033[0m' # No Color

section() {
	# printf "⚡️ ${COLOR}%s${NC}\n" "$*"
	printf "${COLOR}%s${NC}\n" "$*"
}

sectionOK() {
	printf "💾 ${COLOR}%s${NC}\n" "$*"
}

executa2() {
	printf "✅ ${COLOR2}%s${NC}\n" "$*"
}

executa() {
	printf "✅ ${COLOR2}%s${NC}\n" "$*"
	"$@"
}

alert() {
	printf "⚠️ ${COLOR2}%s${NC}\n" "$*"
}

# Parse `-y` and `--yes` script args
YES_ARG=false
argi=0
while (( argi <= $# )); do
    case "${!argi}" in
        -y|--yes) YES_ARG=true ;;
    esac
    ((argi++))
done

# Helper to prompt before continue (default to yes)
confirmYes() {
    # Auto‑accept when invoked with `-y` or `--yes`
    if $YES_ARG; then
    	[[ true ]]
    else
    	# Userprompt
    	local prompt="$1"
    	read -r -p "$prompt [n/Y] " reply
    	[[ -z "$reply" || "$reply" =~ ^[Yy] ]]
   	fi
}

# The libraries
LIBRARIES=(
	"assimp"
	"blend2d"
	"brotli"
	"cairo"
	"cpp-httplib"
	"fmt"
	"freetype"
	"glew"
	"glfw"
	"glm"
	"json"
	"kissfft"
	"libusb"
	#"mango"
	#"mango2"
	"opencv"
	# "opencv-dnn"
	"openssl-curl"
	"pixman"
	"poco"
	"pugixml"
	"rtAudio"
	"tess2"
	"uriparser"
	"utfcpp"
	# "videoInput"
	"yaml-cpp"
	"zlib-ng"
	"zstd"
)

# To enable a single lib
# LIBRARIES=( "openssl-curl" )

# tmp: to enable problematic libs on osx 10.15
if false; then
	LIBRARIES=(
		"mango"
		#error "MANGO requires C++20 or later."
		"mango2"
		#error "MANGO requires C++20 or later."
		"opencv-dnn"
		# ERROR: There was a problem resolving the included paths for the 'opencv-dnn' target. Check that they exist and glob patterns can be resolved.
		# ERROR: chalet.yaml: Distribution target 'opencv-dnn' has an unsupported variable in: ${externalBuild:opencv-dnn}/install/include
		# ERROR: chalet.yaml: External dependency 'opencv-dnn' does not exist.
		"videoInput"
		# FAILED: [code=1] CMakeFiles/videoInput.dir/videoInput.cpp.o 
		# 	/usr/bin/clang++  -I/ofLibs/videoInput/videoInput/. -O3 -DNDEBUG -arch x86_64 -isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk -mmacosx-version-min=10.15 -fPIC -MD -MT CMakeFiles/videoInput.dir/videoInput.cpp.o -MF CMakeFiles/videoInput.dir/videoInput.cpp.o.d -o CMakeFiles/videoInput.dir/videoInput.cpp.o -c /ofLibs/videoInput/videoInput/videoInput.cpp
		# 	In file included from /ofLibs/videoInput/videoInput/videoInput.cpp:11:
		# 	/ofLibs/videoInput/videoInput/./videoInput.h:56:10: fatal error: 'windows.h' file not found
		# 	#include <windows.h>
	)
fi

LIBRARIES_COUNT=${#LIBRARIES[@]}

# HelloWorld
section "Welcome to the ofLibs compilation script"
echo " - There are $LIBRARIES_COUNT libraries."

# Execute
if confirmYes " - Continue with compilation ?"; then
	SUCCESS=0
    FAILURES=0

    if [[ ${#LIBRARIES[@]} -gt 0 ]]; then
		for LIBRARY_FOLDER in "${LIBRARIES[@]}"; do
		    section "Compiling ${LIBRARY_FOLDER}..."
		    cd ./${LIBRARY_FOLDER}

		    skipped=0
		    # Chalet project ?
		    if [[ -f "./chalet.yaml" ]]; then
				chalet bundle
			# Bash script ?
			elif [[ -f "./$LIBRARY_FOLDER.sh" ]]; then
				./${LIBRARY_FOLDER}.sh
			else
				alert "Skipping compilation of ${LIBRARY_FOLDER}. It's not a chalet project neither a bash script."
				skipped=1
			fi

			# Count failures
			if [[ $? -eq 0 && skipped -eq 0 ]]; then
	            ((SUCCESS++))
	        else
	            ((FAILURES++))
	        fi
			cd ../
		done
	fi

	echo " "
	sectionOK "Successfully compiled $SUCCESS/$LIBRARIES_COUNT libraries !"
	[[ $FAILURES -gt 0 ]] && alert "${FAILURES} libraries failed to build!"
else
	echo "Bye bye."
fi
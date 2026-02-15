#!/bin/bash

# Script to build Lambda deployment packages

set -e

echo "Building Lambda deployment packages..."

# Create build directory
BUILD_DIR="lambda_packages"
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR

# Lambda functions to package
FUNCTIONS=("upload_presigned_url" "complete_upload" "list_images" "get_image_presigned_url" "delete_image")

for FUNC in "${FUNCTIONS[@]}"; do
    echo "Building $FUNC..."
    
    # Create temporary directory for this function
    TEMP_DIR="$BUILD_DIR/$FUNC"
    mkdir -p $TEMP_DIR
    
    # Copy source code
    cp -r src $TEMP_DIR/
    
    # Install dependencies
    pip install -r requirements.txt -t $TEMP_DIR/ --quiet
    
    # Create ZIP file
    cd $TEMP_DIR
    zip -r ../${FUNC}.zip . -q
    cd ../..
    
    echo "✓ Created ${FUNC}.zip"
done

echo ""
echo "All Lambda packages built successfully in $BUILD_DIR/"
ls -lh $BUILD_DIR/*.zip

import os
import sys
import subprocess

def get_file_size_mb(file_path):
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb

def compress_with_handbrake(original_file):
    # Get original file size
    original_size_mb = get_file_size_mb(original_file)
    print(f"Original file size: {original_size_mb:.2f} MB")

    output_file = original_file.replace(".mp4", "-hbed.mp4")
    
    # HandBrake CLI command to compress the video
    handbrake_command = [
        "HandBrakeCLI",
        "-i", original_file,
        "-o", output_file,
        "-Y", "2160",
        "-X", "3840",
        "--preset", "Fast 1080p30"  # change this preset as needed
    ]
    
    print(f"Compressing {original_file} to {output_file}...")
    result = subprocess.run(handbrake_command, capture_output=True, text=True)
    
    if result.returncode == 0:
        compressed_size_mb = get_file_size_mb(output_file)
        size_saved_mb = original_size_mb - compressed_size_mb
        print(f"original:{original_size_mb:.2f} MB, compressed:{compressed_size_mb:.2f} MB, saved:{size_saved_mb:.2f} MB")
        return output_file, size_saved_mb
    else:
        print(f"ERROR: HandBrake returned code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        print(f"STDOUT: {result.stdout}")
        return None, 0, 0

def apply_tags(original_file, compressed_file):
    """Copy metadata from the original file to the compressed file"""
    # Call exiftool
    result = subprocess.run(["exiftool", "-TagsFromFile", original_file, compressed_file])
    if result.returncode == 0:
        print(f"Tags applied from {original_file} to {compressed_file}")
        return True
    else:
        print(f"Error applying tags")
        return False

def main():
    folder_path = sys.argv[1]

    # Track total savings
    total_saved_size = 0
    
    # Iterate through files in the folder
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".mp4") and "-hbed" not in file_name:
            original_file = os.path.join(folder_path, file_name)
            
            result = compress_with_handbrake(original_file)
            
            if result and result[0]:
                compressed_file, size_saved_mb = result
                total_saved_size += size_saved_mb
                # Step 2: Copy metadata with ExifTool
                tags_success = apply_tags(original_file, compressed_file)
                
                if tags_success:
                    artifact = compressed_file + "_original"
                    os.remove(artifact)
                    print(f"{artifact} deleted.")
                    # Step 3: Remove the original file
                    os.remove(original_file)
                    print(f"Original file {original_file} deleted.")
                else:
                    print(f"Skipping deletion of {original_file} due to tag application failure.")

    print(f"Compressed total size: {total_saved_size:.2f} MB")

if __name__ == "__main__":
    main()

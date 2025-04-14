import argparse
import os
import sys
import subprocess

def get_file_size_mb(file_path):
    """Get the size of a file in megabytes."""
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb

def compress_with_handbrake(original_file, verbose_output=False):
    original_size_mb = get_file_size_mb(original_file)
    print(f"Original file size: {original_size_mb:.2f} MB")

    """Compress the video file using HandBrake CLI"""
    output_file = original_file.replace(".mp4", "-hbed.mp4")
    
    handbrake_command = [
        "C:\\HandBrakeCLI\\HandBrakeCLI.exe",
        "-i", original_file,
        "-o", output_file,
        "-Y", "2160",
        "-X", "3840",
        "--preset", "Fast 1080p30"  # change this preset as needed
    ]
    
    print(f"Compressing {original_file} to {output_file}...")
    
    # Run the process with real-time output streaming
    process = subprocess.Popen(
        handbrake_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Track progress stages
    current_stage = "Preparing"
    last_percentage = 0
    scanning_complete = False
    
    def print_progress_bar(percentage, stage="Processing"):
        """Print a progress bar with the current percentage"""
        bar_length = 40
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\r{stage}: [{bar}] {percentage:.1f}%", end='', flush=True)
    
    # Print output in real-time, but only show progress
    try:
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                print()
                break
            
            if output:
                if verbose_output:
                    print(output.strip())
                
                # Check for completion markers first
                if "Encode done!" in output or "HandBrake has exited" in output:
                    if current_stage == "Encoding" and last_percentage > 0:
                        # Make sure we show 100% when complete
                        print_progress_bar(100.0, current_stage)
                    continue
                
                # Extract scanning percentage
                if "Scanning title" in output and "%" in output:
                    try:
                        percentage = float(output.split("%")[0].split(",")[-1].strip())
                        if percentage > last_percentage:
                            last_percentage = percentage
                            current_stage = "Scanning"
                            print_progress_bar(percentage, current_stage)
                    except ValueError:
                        pass
                
                # Extract encoding percentage
                elif "Encoding: task" in output and "%" in output:
                    try:
                        parts = output.split("%")[0].split(",")
                        percentage = float(parts[-1].strip())
                        
                        # Only when we see first encoding percentage, print a newline to separate from scanning
                        if not scanning_complete and "Encoding" in output:
                            scanning_complete = True
                            print_progress_bar(100, current_stage)
                            print()  # New line after scanning completes
                            last_percentage = 0  # Reset for encoding percentage
                        
                        if percentage > last_percentage:
                            last_percentage = percentage
                            current_stage = "Encoding"
                            print_progress_bar(percentage, current_stage)
                            
                            # Print ETA if available
                            if "ETA" in output:
                                eta = output.split("ETA")[1][:9].strip()
                                print(f" (ETA: {eta})", end='', flush=True)
                    except ValueError:
                        pass
        
        # Make sure we finish with a newline
        print()
        
        # Wait for the process to fully complete
        process.wait()
        return_code = process.returncode
        
        if return_code == 0:
            # Verify the output file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                compressed_size_mb = get_file_size_mb(output_file)
                size_saved_mb = original_size_mb - compressed_size_mb
                
                print(f"original: {original_size_mb:.2f} MB, compressed: {compressed_size_mb:.2f} MB, saved: {size_saved_mb:.2f} MB")
                return output_file, size_saved_mb
            else:
                print(f"ERROR: HandBrake output file {output_file} does not exist or is empty")
                return None, 0
        else:
            print(f"ERROR: HandBrake returned code {return_code}")
            return None, 0
            
    except Exception as e:
        # Handle any errors in the output processing
        print(f"ERROR: An exception occurred while processing HandBrake output: {e}")
        try:
            # Try to terminate the process if it's still running
            if process.poll() is None:
                process.terminate()
        except:
            pass
        return None, 0

def apply_tags(original_file, compressed_file):
    """Copy metadata from the original file to the compressed file"""
    result = subprocess.run(["C:\\dev\\exiftool-13.25_64\\exiftool.exe", "-TagsFromFile", original_file, compressed_file])
    if result.returncode == 0:
        print(f"Tags applied from {original_file} to {compressed_file}")
        return True
    else:
        print(f"Error applying tags: {result.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Compress video files using HandBrake and copy metadata with ExifTool")
    parser.add_argument("folder_path", help="Path to the folder containing video files")
    parser.add_argument("--delete", action="store_true", help="Delete original files after successful compression (default: False)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Display detailed HandBrake output (default: False)")
   
    args = parser.parse_args()
    folder_path = args.folder_path
    delete_originals = args.delete
    verbose_output = args.verbose

    total_saved_size = 0
    
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".mp4") and "-hbed" not in file_name:
            original_file = os.path.join(folder_path, file_name)
            
            result = compress_with_handbrake(original_file, verbose_output)
            
            if result and result[0]:
                compressed_file, size_saved_mb = result
                total_saved_size += size_saved_mb
                # Step 2: Copy metadata with ExifTool
                tags_success = apply_tags(original_file, compressed_file)
                
                if tags_success:
                    artifact = compressed_file + "_original"
                    os.remove(artifact)
                    print(f"{artifact} deleted.")
                    if delete_originals:
                        os.remove(original_file)
                        print(f"Original file {original_file} deleted.")
                else:
                    print(f"Skipping deletion of {original_file} due to tag application failure.")

    print(f"Compressed total size: {total_saved_size:.2f} MB")

if __name__ == "__main__":
    main()

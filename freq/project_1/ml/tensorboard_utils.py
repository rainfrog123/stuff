import os
import subprocess
import time
import shutil

def clear_tensorboard_logs():
    """Clear existing TensorBoard logs."""
    if os.path.exists('lightning_logs'):
        shutil.rmtree('lightning_logs')
    os.makedirs('lightning_logs', exist_ok=True)

def setup_directories():
    """Setup necessary directories for the project."""
    directory_path = os.getcwd()
    checkpoint_dir = os.path.join(directory_path, 'checkpoints')
    os.makedirs(checkpoint_dir, exist_ok=True)
    return directory_path, checkpoint_dir

def start_tensorboard(port=6006):
    """Start TensorBoard in background."""
    print("Starting TensorBoard dashboard...")
    tensorboard_process = subprocess.Popen(
        ["tensorboard", "--logdir", "lightning_logs", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print(f"TensorBoard started! Visit http://localhost:{port} to view the dashboard")
    time.sleep(3)  # Give TensorBoard time to start
    return tensorboard_process 
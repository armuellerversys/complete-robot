import sys
import os
import time
import asyncio
import subprocess
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

# Optional evdev import for Linux/Raspberry Pi GamePad handling
try:
    import evdev
    from evdev import ecodes
except ImportError:
    evdev = None


# =====================================================================
# 1. FLASK SUBPROCESS MANAGEMENT
# =====================================================================
def start_flask_subprocess(queue: multiprocessing.Queue) -> subprocess.Popen:
    """Starts the Flask webserver script as a subprocess."""
    # Pass the queue or connection mechanism required by your Flask setup
    process = subprocess.Popen(
        [sys.executable, "image_app_core.py"],
        env=os.environ.copy()
    )
    return process


# =====================================================================
# 2. SHARED COMMAND HANDLER
# =====================================================================
async def handle_command(source: str, command: dict):
    """
    Unified entry point for both HTTP and GamePad commands.
    Keep processing fast/non-blocking or offload heavy tasks.
    """
    cmd_type = command.get("type")
    payload = command.get("payload")

    # Example dispatch logic
    if cmd_type == "MOVE":
        # Process motor/vehicle movement
        pass
    elif cmd_type == "STOP":
        # Execute stop
        pass
    else:
        pass


# =====================================================================
# 3. HTTP QUEUE LISTENER (Threading Executor for Blocking IPC Queue)
# =====================================================================
def poll_queue_blocking(ipc_queue: multiprocessing.Queue):
    """Blocking worker intended to run in a background thread executor."""
    while True:
        try:
            # Blocking read with a short timeout to allow clean shutdown checks
            item = ipc_queue.get(timeout=0.1)
            yield item
        except Exception:
            # Timeout hit, continue loop
            continue


async def http_queue_worker(ipc_queue: multiprocessing.Queue):
    """Async task that bridges the blocking IPC queue to the async loop."""
    loop = asyncio.get_running_loop()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        while True:
            # Run blocking queue reads in a thread pool without blocking the loop
            try:
                command = await loop.run_in_executor(executor, ipc_queue.get, True, 0.1)
                await handle_command(source="HTTP", command=command)
            except Exception:
                # Queue empty (timeout), yield execution back to loop
                await asyncio.sleep(0.01)


# =====================================================================
# 4. BLUETOOTH GAMEPAD LISTENER (Native Async with evdev)
# =====================================================================
async def gamepad_worker(device_path: str = "/dev/input/event0"):
    """Async task that continuously reads Bluetooth GamePad inputs."""
    if evdev is None:
        print("[GamePad] evdev module not installed. Skipping GamePad worker.")
        return

    try:
        device = evdev.InputDevice(device_path)
        print(f"[GamePad] Connected to {device.name} at {device_path}")

        # device.async_read_loop() natively yields events to asyncio
        async for event in device.async_read_loop():
            if event.type == ecodes.EV_KEY:
                # Key / Button Press Event
                key_event = evdev.categorize(event)
                cmd = {
                    "type": "BUTTON",
                    "payload": {"code": event.code, "state": event.value}
                }
                await handle_command(source="GamePad", command=cmd)

            elif event.type == ecodes.EV_ABS:
                # Joystick / Analog Axis Event
                cmd = {
                    "type": "AXIS",
                    "payload": {"axis": event.code, "value": event.value}
                }
                await handle_command(source="GamePad", command=cmd)

    except (FileNotFoundError, PermissionError) as e:
        print(f"[GamePad] Error accessing device at {device_path}: {e}")
    except asyncio.CancelledError:
        print("[GamePad] Worker shutting down.")


# =====================================================================
# 5. MAIN ASYNC ENTRY POINT
# =====================================================================
async def main():
    # Multiprocessing Queue for Flask <-> Main IPC
    ipc_queue = multiprocessing.Queue()

    # Start Flask Webserver Subprocess
    flask_proc = start_flask_subprocess(ipc_queue)

    try:
        # Schedule both processing loops concurrently
        await asyncio.gather(
            http_queue_worker(ipc_queue),
            gamepad_worker(device_path="/dev/input/event0")  # Adjust device path as needed
        )
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
    finally:
        # Clean up subprocess
        flask_proc.terminate()
        flask_proc.wait()


if __name__ == "__main__":
    asyncio.run(main())
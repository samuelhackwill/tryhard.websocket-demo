import asyncio
from evdev import InputDevice, ecodes
import glob
import websockets
import socket
import json

# Path to input devices by ID
DEVICES_PATH = "/dev/input/by-id"
raspName = socket.gethostname()

async def read_mouse_events(device_path, queue):
    """Read mouse events from a specific device."""
    device = InputDevice(device_path)
    print(f"Listening on device: {device.name} ({device.path})")
    async for event in device.async_read_loop():
        if event.type == ecodes.EV_REL:  # Relative motion (mouse movement)
            # Queue the mouse motion event
            await queue.put({
                "client":raspName,
                "device": device.path,
                "event_type": "motion",
                "code": ecodes.REL[event.code],
                "value": event.value
            })
        elif event.type == ecodes.EV_KEY:  # Button press or release
            # Queue the button event
            await queue.put({
                "client":raspName,
                "device": device.path,
                "event_type": "button",
                "code": ecodes.BTN[event.code],
                "value": "pressed" if event.value == 1 else "released"
            })
        elif event.type == ecodes.EV_REL and event.code in (ecodes.REL_WHEEL, ecodes.REL_HWHEEL):  # Mouse wheel
            # Queue the mouse wheel event
            direction = "up" if event.value > 0 else "down"
            if event.code == ecodes.REL_HWHEEL:
                direction = "right" if event.value > 0 else "left"
            await queue.put({
                "client":raspName,
                "device": device.path,
                "event_type": "wheel",
                "code": ecodes.REL[event.code],
                "value": direction
            })

async def monitor_mice(queue):
    """Monitor all connected mice under /dev/input/by-id."""
    mice_tasks = []
    # Find all mouse devices
    for device_path in glob.glob(f"{DEVICES_PATH}/*-event-mouse"):
        mice_tasks.append(asyncio.create_task(read_mouse_events(device_path, queue)))
    print(f"Monitoring {len(mice_tasks)} mice...")
    # Wait for all mice tasks to complete
    await asyncio.gather(*mice_tasks)

async def send_to_websocket(queue, server_uri):
    """Connect to the WebSocket server and send mouse events."""
    while True:
        try:
            # Attempt to connect to the WebSocket server
            async with websockets.connect(
                server_uri,
                ping_interval=5,  # Adjust to match server's ping interval
                ping_timeout=10   # Timeout for ping responses
            ) as websocket:
                print(f"Connected to WebSocket server at {server_uri}")
                
                async def handle_pings():
                    """Handle incoming ping messages."""
                    while True:
                        try:
                            await websocket.recv()  # Wait for any messages (e.g., pings)
                        except websockets.ConnectionClosed:
                            print("Connection closed during ping handling.")
                            break

                # Start the ping handler
                asyncio.create_task(handle_pings())
            
                while True:
                    # Get data from the queue
                    data = await queue.get()
                    
                    # Convert the data to JSON and send it
                    json_data = json.dumps(data)
                    await websocket.send(json_data)
                    print(f"Sent data to server: {json_data}")

        except websockets.ConnectionClosedError as e:
            print(f"Connection closed unexpectedly: {e}")
            await asyncio.sleep(5)  # Wait before reconnecting

        except Exception as e:
            print(f"Unexpected error: {e}")
            await asyncio.sleep(5)  # Wait before reconnecting

async def main():
    queue = asyncio.Queue()

    # Replace with the WebSocket server's IP and port
    server_uri = "ws://192.168.1.64:8080"  # Example: ws://192.168.1.100:8080

    # Start monitoring mice
    mice_task = asyncio.create_task(monitor_mice(queue))
    
    # Start sending data to the WebSocket server
    websocket_task = asyncio.create_task(send_to_websocket(queue, server_uri))
    
    # Wait for both tasks to complete (they won't unless interrupted)
    await asyncio.gather(mice_task, websocket_task)

if __name__ == "__main__":
    asyncio.run(main())

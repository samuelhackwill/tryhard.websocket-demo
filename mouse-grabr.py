import asyncio
import random
import websockets
import socket
import json

async def generate_fake_device_data(queue, device_id):
    """Simulate mouse movement data for a fake device."""
    hostname = socket.gethostname()  # Get the host name of the device
    xOrY = ["REL_Y", "REL_X"]
    while True:
        # Generate random relative X and Y movements
        data = {
            "client": hostname,
            "device": f"simulatedMouse_{device_id}",
            "event_type": "motion",
            "code": xOrY[random.randint(0, 1)],
            "value": random.randint(-10, 10)          
            }
        await queue.put(data)  # Add the data to the queue
        await asyncio.sleep(1 / 50)  # 50 signals per second

async def simulate_devices(queue, num_devices):
    """Simulate multiple fake devices generating data."""
    tasks = [asyncio.create_task(generate_fake_device_data(queue, i)) for i in range(num_devices)]
    await asyncio.gather(*tasks)

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

    # Start simulating devices
    num_devices = 4  # Number of fake devices
    device_simulation_task = asyncio.create_task(simulate_devices(queue, num_devices))

    # Start sending data to the WebSocket server
    websocket_task = asyncio.create_task(send_to_websocket(queue, server_uri))

    # Wait for both tasks to complete (they won't unless interrupted)
    await asyncio.gather(device_simulation_task, websocket_task)

if __name__ == "__main__":
    asyncio.run(main())

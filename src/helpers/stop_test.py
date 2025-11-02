import asyncio
import json
import sys

async def send_stop_command(state: bool = True, reason: str = "Manual stop", socket_path: str = "/tmp/mech-control.sock"):
    try:
        # Connect to the Unix socket
        reader, writer = await asyncio.open_unix_connection(socket_path)
        
        # Create command
        command = {
            "command": "stop_mechanism",
            "state": state,
            "reason": reason
        }
        
        # Send command
        writer.write((json.dumps(command) + '\n').encode())
        await writer.drain()
        
        # Get response
        response = await reader.readline()
        print(f"Response: {response.decode().strip()}")
        
        # Close connection
        writer.close()
        await writer.wait_closed()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    state = True if len(sys.argv) > 1 and sys.argv[1].lower() == 'true' else False
    reason = sys.argv[2] if len(sys.argv) > 2 else "Manual stop"
    
    asyncio.run(send_stop_command(state, reason))

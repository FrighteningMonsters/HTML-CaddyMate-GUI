# CaddyMate GUI

A touch-friendly GUI for a 7-inch display designed for elderly users.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Regenerate database with ROS coordinates for TurtleBot navigation:
```bash
python data/Database_Creator.py
```

## Running the Application

1. Start the Flask server:
```bash
python server.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

The server will:
- Serve the HTML pages
- Provide API endpoints for categories and items from the SQLite database

## Pages

- **home.html** - Main menu with Browse Categories and Search Items buttons
- **motor.html** - Dedicated hold-to-run up/down motor controls
- **categories.html** - Displays all product categories from the database
- **search.html** - Search for items and navigate directly to the map

## API Endpoints

- `GET /api/categories` - Get all categories
- `GET /api/items` - Get all items for search
- `GET /api/items/<category_id>` - Get items for a specific category

## Database

The application uses SQLite database located at `data/caddymate_store.db` with the following structure:

### Tables:
- **categories** (id, name)
- **items** (id, name, category_id, aisle, aisle_position, x_ros, y_ros, yaw_ros)

## TurtleBot Integration

When `lobby_final.pgm` and `lobby_final.yaml` (SLAM map) are in the project root, the map page loads the SLAM map and connects to ROS via rosbridge.

1. Ensure rosbridge is running on the Dice Machine: `ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090`
2. Edit `ros_config.json` to set `rosbridge_host` to the Dice Machine IP (e.g. `129.215.3.31`)
3. Items with `x_ros`, `y_ros`, `yaw_ros` coordinates show a "Navigate Here" button on the map page

## Arduino Motor Control (Home Screen)

The home screen includes hold-to-run up/down arrow buttons for a motorized base:

- Press and hold the up arrow to send `UP` continuously (motor runs while held)
- Press and hold the down arrow to send `DOWN` continuously (motor runs while held)
- Releasing either button sends `STOP`

The Flask backend sends commands to an Arduino Uno over serial.

Expected Arduino commands are newline-terminated strings: `UP`, `DOWN`, and `STOP`.

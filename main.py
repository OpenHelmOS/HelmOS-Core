from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import asyncio
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

led_state = {"state": "off"}
connected_clients = []
main_loop = None

@app.on_event("startup")
async def startup():
    global main_loop
    main_loop = asyncio.get_event_loop()

def on_message(client, userdata, message):
    payload = message.payload.decode()
    led_state["state"] = payload
    if main_loop:
        asyncio.run_coroutine_threadsafe(notify_clients(payload), main_loop)

async def notify_clients(state):
    for ws in connected_clients.copy():
        try:
            await ws.send_text(json.dumps({"state": state}))
        except:
            connected_clients.remove(ws)

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883)
mqtt_client.subscribe("helmos/led")
mqtt_client.loop_start()

@app.get("/led")
def get_led():
    return led_state

@app.post("/led/{state}")
def set_led(state: str):
    mqtt_client.publish("helmos/led/set", state)
    return {"state": state}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    await websocket.send_text(json.dumps(led_state))
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)

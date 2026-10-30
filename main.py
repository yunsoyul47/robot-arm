
import streamlit as st
import streamlit.components.v1 as components
import serial
from serial.tools import list_ports
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
import threading
import time

# ==========================================
# ROBOT ARM CONTROLLER
# Arduino UNO / 30kg + 6kg Servo
# ==========================================

st.set_page_config(
    page_title="ROBOT ARM CONTROL",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# SERIAL CONTROLLER
# ==========================================

class RobotController:

    def __init__(self):
        self.ser = None
        self.port = None
        self.angle30 = 90
        self.angle6 = 90
        self.lock = threading.Lock()
        self.error = ""

    def connect(self, port):

        with self.lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()

                self.ser = serial.Serial(
                    port,
                    9600,
                    timeout=1,
                    write_timeout=1
                )

                self.port = port

                # Arduino 재시작 대기
                time.sleep(2)

                self.ser.reset_input_buffer()

                self.angle30 = 90
                self.angle6 = 90

                self.ser.write(b'R')

                self.error = ""
                return True

            except Exception as e:
                self.ser = None
                self.port = None
                self.error = str(e)
                return False

    def disconnect(self):

        with self.lock:
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass

            self.ser = None
            self.port = None

    def command(self, cmd):

        with self.lock:

            if not self.ser or not self.ser.is_open:
                return {
                    "success": False,
                    "message": "Arduino is not connected"
                }

            try:

                if cmd == "W":
                    self.angle30 = min(170, self.angle30 + 5)

                elif cmd == "S":
                    self.angle30 = max(10, self.angle30 - 5)

                elif cmd == "A":
                    self.angle6 = min(170, self.angle6 + 5)

                elif cmd == "D":
                    self.angle6 = max(10, self.angle6 - 5)

                elif cmd == "R":
                    self.angle30 = 90
                    self.angle6 = 90

                else:
                    return {
                        "success": False,
                        "message": "Invalid command"
                    }

                self.ser.write(cmd.encode("ascii"))

                return {
                    "success": True,
                    "angle30": self.angle30,
                    "angle6": self.angle6
                }

            except Exception as e:

                self.error = str(e)

                return {
                    "success": False,
                    "message": str(e)
                }

    def status(self):

        with self.lock:
            connected = (
                self.ser is not None
                and self.ser.is_open
            )

            return {
                "connected": connected,
                "port": self.port,
                "angle30": self.angle30,
                "angle6": self.angle6,
                "error": self.error
            }


# ==========================================
# SHARED CONTROLLER
# ==========================================

@st.cache_resource
def get_controller():
    return RobotController()


controller = get_controller()


# ==========================================
# LOCAL SERIAL BRIDGE
# ==========================================

@st.cache_resource
def start_bridge():

    app = Flask("robot_arm_bridge")

    @app.after_request
    def add_cors(response):

        origin = request.headers.get("Origin", "")

        if (
            origin == "null"
            or origin.startswith("http://localhost:")
            or origin.startswith("http://127.0.0.1:")
        ):
            response.headers["Access-Control-Allow-Origin"] = origin

        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )

        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type"
        )

        return response

    @app.route("/status", methods=["GET"])
    def get_status():

        return jsonify(controller.status())

    @app.route("/command", methods=["POST"])
    def send_command():

        cmd = request.get_data(as_text=True).strip().upper()

        result = controller.command(cmd)

        return jsonify(result)

    server = make_server(
        "127.0.0.1",
        8765,
        app,
        threaded=True
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    return server


start_bridge()


# ==========================================
# DESIGN CSS
# ==========================================

st.markdown("""
<style>

.stApp {
    background-color: #080e1b;
    color: #e7efff;
}

header[data-testid="stHeader"] {
    background-color: #080e1b;
}

.block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

h1, h2, h3 {
    color: #e8f2ff !important;
}

.robot-header {
    background: linear-gradient(
        120deg,
        #102b4c,
        #10172b,
        #102c3d
    );
    padding: 30px;
    border: 1px solid #214c72;
    border-radius: 18px;
    margin-bottom: 25px;
}

.robot-header h1 {
    font-size: 38px;
    letter-spacing: 4px;
    margin-bottom: 5px;
}

.robot-header p {
    color: #8daecb;
    letter-spacing: 2px;
}

.panel {
    background: #111c30;
    border: 1px solid #263b59;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 15px;
}

.status {
    color: #46e5a2;
    font-weight: bold;
}

.small-text {
    color: #8da6c4;
    font-size: 13px;
}

div.stButton > button {
    background: #172d49;
    color: #e8f2ff;
    border: 1px solid #35618c;
    border-radius: 10px;
    min-height: 45px;
}

div.stButton > button:hover {
    background: #23527c;
    color: white;
    border-color: #50bfff;
}

[data-testid="stMetric"] {
    background: #111c30;
    border: 1px solid #263b59;
    padding: 15px;
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# HEADER
# ==========================================

st.markdown("""
<div class="robot-header">

    <p>ADVANCED ROBOTICS SYSTEM / 2026</p>

    <h1>🤖 ROBOT ARM CONTROL</h1>

    <p>DUAL SERVO MOTOR · ARDUINO UNO</p>

</div>
""", unsafe_allow_html=True)


# ==========================================
# CONNECTION
# ==========================================

st.subheader("01 / DEVICE CONNECTION")

ports = list(list_ports.comports())

port_options = {
    f"{p.device}  |  {p.description}": p.device
    for p in ports
}

col1, col2, col3 = st.columns([2, 1, 1])

with col1:

    if port_options:

        selected_label = st.selectbox(
            "Arduino COM PORT",
            list(port_options.keys())
        )

        selected_port = port_options[selected_label]

    else:

        selected_port = None

        st.warning(
            "연결된 COM 포트를 찾을 수 없습니다."
        )

with col2:

    st.write(" ")

    if st.button(
        "CONNECT",
        use_container_width=True
    ):

        if selected_port:

            success = controller.connect(selected_port)

            if success:
                st.success("Arduino 연결 성공!")

            else:
                st.error(controller.error)

        else:
            st.error("COM 포트를 먼저 선택하세요.")

with col3:

    st.write(" ")

    if st.button(
        "DISCONNECT",
        use_container_width=True
    ):

        controller.disconnect()
        st.info("연결이 해제되었습니다.")


# ==========================================
# CONNECTION STATUS
# ==========================================

status = controller.status()

if status["connected"]:

    st.success(
        f"● ONLINE  |  {status['port']}  |  Arduino UNO 연결됨"
    )

else:

    st.error("● OFFLINE  |  Arduino 연결 필요")


st.divider()


# ==========================================
# MOTOR INFORMATION
# ==========================================

st.subheader("02 / MOTOR MONITOR")

status = controller.status()

m1, m2 = st.columns(2)

with m1:

    st.metric(
        "30KG SERVO MOTOR",
        f"{status['angle30']}°",
        help="좌우 회전 관절"
    )

    st.caption("BASE ROTATION / 좌우 회전")

with m2:

    st.metric(
        "6KG SERVO MOTOR",
        f"{status['angle6']}°",
        help="상하 회전 관절"
    )

    st.caption("ARM ROTATION / 상하 회전")


st.divider()


# ==========================================
# ROBOT ARM KEYBOARD CONTROL
# ==========================================

st.subheader("03 / MANUAL CONTROL")

st.caption(
    "방향키를 누르거나 아래 버튼을 클릭하여 로봇팔을 조작하세요."
)

html = r"""
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">

<style>

* {
    box-sizing: border-box;
}

body {
    background: #080e1b;
    color: #e8f2ff;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 12px;
}

.container {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
}

.control-panel {
    background: #111c30;
    border: 1px solid #29415f;
    border-radius: 16px;
    padding: 22px;
    flex: 1;
    min-width: 260px;
}

h3 {
    color: #69c9ff;
    letter-spacing: 2px;
    font-size: 15px;
}

.description {
    color: #91a8c5;
    font-size: 12px;
    margin-bottom: 18px;
}

.keypad {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;
    max-width: 300px;
    margin: auto;
}

.key {
    height: 68px;
    background: #1b3452;
    border: 1px solid #3c6c9c;
    border-radius: 12px;
    color: white;
    font-size: 25px;
    font-weight: bold;
    cursor: pointer;
    transition: 0.1s;
}

.key:hover {
    background: #245b88;
    border-color: #61c7ff;
}

.key:active {
    background: #1477b9;
    transform: scale(0.95);
}

.center {
    background: #0b192a;
    border: 1px solid #29415f;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: #78b8e7;
    text-align: center;
}

.arm-buttons {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 30px;
}

.arm-button {
    height: 100px;
    width: 100px;
    border-radius: 14px;
    background: #1b3452;
    color: white;
    border: 1px solid #3c6c9c;
    font-size: 30px;
    cursor: pointer;
}

.arm-button:hover {
    background: #245b88;
}

.arm-button small {
    display: block;
    font-size: 11px;
    color: #9dc8ec;
    margin-top: 7px;
}

.angle {
    font-size: 28px;
    font-weight: bold;
    color: #59c7ff;
    text-align: center;
    margin-top: 22px;
}

.reset {
    width: 100%;
    margin-top: 22px;
    padding: 15px;
    border-radius: 10px;
    background: #24425e;
    color: white;
    border: 1px solid #5482a9;
    cursor: pointer;
    font-weight: bold;
}

.reset:hover {
    background: #315c80;
}

.info {
    color: #8ba5c2;
    font-size: 12px;
    text-align: center;
    margin-top: 18px;
}

.connection {
    text-align: center;
    color: #ffc66b;
    font-size: 13px;
    margin-top: 12px;
}

</style>
</head>

<body tabindex="0">

<div class="container">

    <!-- BASE MOTOR -->

    <div class="control-panel">

        <h3>30KG MOTOR / BASE</h3>

        <div class="description">
            좌우 회전 관절 (BASE ROTATION)
        </div>

        <div class="keypad">

            <div></div>

            <div class="center">
                좌우 회전
            </div>

            <div></div>

            <button class="key" data-cmd="S">←</button>

            <div class="center">
                <span id="angle30">90°</span>
            </div>

            <button class="key" data-cmd="W">→</button>

            <div></div>

            <div></div>

            <div></div>

        </div>

        <div class="angle" id="base-angle">
            90°
        </div>

        <div class="info">
            ← 감소 (-5°) &nbsp; | &nbsp; → 증가 (+5°)
        </div>

    </div>


    <!-- ARM MOTOR -->

    <div class="control-panel">

        <h3>6KG MOTOR / ARM</h3>

        <div class="description">
            상하 회전 관절 (ARM ROTATION)
        </div>

        <div class="arm-buttons">

            <button class="arm-button" data-cmd="A">
                ↑
                <small>위로 (+5°)</small>
            </button>

            <button class="arm-button" data-cmd="D">
                ↓
                <small>아래로 (-5°)</small>
            </button>

        </div>

        <div class="angle" id="arm-angle">
            90°
        </div>

        <div class="info">
            ↑ 증가 (+5°) &nbsp; | &nbsp; ↓ 감소 (-5°)
        </div>

    </div>

</div>


<button class="reset" id="reset">
    ↺ RESET POSITION / 초기 위치 복귀
</button>

<div class="connection" id="connection">
    연결 상태 확인 중...
</div>

<div class="info">
    키보드 방향키를 사용하려면 먼저 이 제어 화면을 클릭하세요.
    <br>
    R 키 : 초기 위치 / Space : 현재 위치 유지
</div>


<script>

const API = "http://127.0.0.1:8765";

let lastCommand = 0;
let angle30 = 90;
let angle6 = 90;

const connection = document.getElementById("connection");

function updateAngles() {

    document.getElementById("angle30").textContent =
        angle30 + "°";

    document.getElementById("base-angle").textContent =
        angle30 + "°";

    document.getElementById("arm-angle").textContent =
        angle6 + "°";

}

async function sendCommand(cmd) {

    const now = Date.now();

    // 너무 빠른 반복 입력 방지
    if (now - lastCommand < 120) {
        return;
    }

    lastCommand = now;

    try {

        const response = await fetch(
            API + "/command",
            {
                method: "POST",
                headers: {
                    "Content-Type": "text/plain"
                },
                body: cmd
            }
        );

        const result = await response.json();

        if (result.success) {

            angle30 = result.angle30;
            angle6 = result.angle6;

            updateAngles();

            connection.textContent =
                "● ONLINE / COMMAND SENT";

            connection.style.color = "#46e5a2";

        } else {

            connection.textContent =
                "● ERROR / " + result.message;

            connection.style.color = "#ff7777";

        }

    } catch (error) {

        connection.textContent =
            "● BRIDGE ERROR / PC 연결을 확인하세요.";

        connection.style.color = "#ff7777";

    }

}


// 화면 버튼 조작

document.querySelectorAll("[data-cmd]").forEach(button => {

    button.addEventListener("click", () => {

        sendCommand(button.dataset.cmd);

    });

});


// 초기 위치 버튼

document.getElementById("reset").addEventListener(
    "click",
    () => sendCommand("R")
);


// 키보드 조작

window.addEventListener("keydown", event => {

    let cmd = null;

    switch(event.key) {

        case "ArrowLeft":
            cmd = "S";
            break;

        case "ArrowRight":
            cmd = "W";
            break;

        case "ArrowUp":
            cmd = "A";
            break;

        case "ArrowDown":
            cmd = "D";
            break;

        case "r":
        case "R":
            cmd = "R";
            break;

        case " ":
            event.preventDefault();
            return;

        default:
            return;
    }

    event.preventDefault();

    sendCommand(cmd);

});


// 연결 상태 확인

async function checkStatus() {

    try {

        const response = await fetch(API + "/status");

        const data = await response.json();

        if (data.connected) {

            angle30 = data.angle30;
            angle6 = data.angle6;

            updateAngles();

            connection.textContent =
                "● ONLINE / " + data.port;

            connection.style.color = "#46e5a2";

        } else {

            connection.textContent =
                "● OFFLINE / Arduino 연결 필요";

            connection.style.color = "#ffc66b";

        }

    } catch(error) {

        connection.textContent =
            "● BRIDGE OFFLINE / 로컬 PC에서 실행하세요.";

        connection.style.color = "#ff7777";

    }

}

setInterval(checkStatus, 700);

checkStatus();

</script>

</body>
</html>
"""

components.html(
    html,
    height=510,
    scrolling=False
)


# ==========================================
# CONTROL INFORMATION
# ==========================================

st.divider()

st.subheader("04 / CONTROL GUIDE")

guide1, guide2 = st.columns(2)

with guide1:

    st.markdown("""
    **30KG BASE MOTOR**

    - ← 왼쪽 회전 (-5°)
    - → 오른쪽 회전 (+5°)

    **6KG ARM MOTOR**

    - ↑ 위쪽 회전 (+5°)
    - ↓ 아래쪽 회전 (-5°)
    """)

with guide2:

    st.markdown("""
    **SYSTEM COMMAND**

    - R : 초기 위치 90°
    - SPACE : 현재 위치 유지
    - 기본 각도 : 90°
    - 작동 범위 : 10° ~ 170°

    **CONNECTION**

    - Arduino UNO
    - Serial 9600 baud
    - USB COM PORT
    """)


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.markdown("""
<div style="
text-align:center;
color:#66829e;
padding:15px;
font-size:12px;
letter-spacing:2px;
">

ROBOTICS CONTROL SYSTEM
<br><br>
ARDUINO UNO / DUAL SERVO / STREAMLIT

</div>
""", unsafe_allow_html=True)

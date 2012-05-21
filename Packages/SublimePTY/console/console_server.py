import win32api
import win32pipe
import win32console
import win32process
import win32con
import time
import win32event
import win32job

Coord = win32console.PyCOORDType
SmallRect = win32console.PySMALL_RECTType

MAX_BUFFER_WIDTH = 160
MAX_BUFFER_HEIGHT = 100

PYTHON_PID = win32process.GetCurrentProcessId()

# import signal
# import sys
# def signal_handler(signal, handler):
#     print("Signal")
# signal.signal(signal.SIGINT, signal_handler)
# def win32error(error):
#     print("WIn32", error)
#     return False


class ConsoleServer(object):

    def __init__(self):
        self._last_lines = {}
        self._last_colors = {}

        win32console.FreeConsole()
        win32console.AllocConsole()
        #self._job = win32job.CreateJobObject(None, str(time.time())) 
        flags = win32process.CREATE_SUSPENDED | win32process.NORMAL_PRIORITY_CLASS | win32process.CREATE_NEW_PROCESS_GROUP | win32process.CREATE_UNICODE_ENVIRONMENT 
        si = win32process.STARTUPINFO()
        si.dwFlags |= win32con.STARTF_USESHOWWINDOW
        (self._handle, self._thandle, self._pid, i2) = win32process.CreateProcess(None, "cmd.exe", None, None, 0, flags, None, '.', si)
        time.sleep(0.2)
        self._con_out = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
        self._con_in = win32console.GetStdHandle(win32console.STD_INPUT_HANDLE)
        #win32job.AssignProcessToJobObject(self._job, self._handle)
        win32process.ResumeThread(self._thandle)

    def set_window_size(self, width, height):
        window_size = SmallRect()
        window_size.Right = 1
        window_size.Bottom = 1
        self._con_out.SetConsoleWindowInfo(True, window_size)
        time.sleep(0.1)

        req_width = min(MAX_BUFFER_WIDTH, width)
        req_height = min(MAX_BUFFER_HEIGHT, height)
        window_size = SmallRect()
        window_size.Right = req_width - 1
        window_size.Bottom = req_height - 1
        self.set_screen_buffer_size(req_width, req_height)
        time.sleep(0.1)

        self._con_out.SetConsoleWindowInfo(True, window_size)

    def set_screen_buffer_size(self, width, height):
        self._con_out.SetConsoleScreenBufferSize(Coord(width, height))

    def terminate_process(self):
        #return win32job.TerminateJobObject(self.job, 1) 
        return win32process.TerminateProcess(self._handle, 0)

    def write_console_input(self, codes):
        self._con_in.WriteConsoleInput(codes)

    def _input_record(self, key, **kwds):
        from win32_keymap import make_input_key
        return make_input_key(key, **kwds)

    def send_keypress(self, key, **kwds):
        self.write_console_input([self._input_record(key, **kwds)])

    def send_ctrl_c(self):
        # ctrl_break for now, it seems I am unable to control
        # ctrl_c correctly, it either does nopthing or kills 
        # controling python process as well
        #win32console.GenerateConsoleCtrlEvent(win32console.CTRL_C_EVENT, self._pid)
        win32console.GenerateConsoleCtrlEvent(win32console.CTRL_BREAK_EVENT, self._pid)

    def send_click(self, row, col, button=1, count=1):
        inputs = []

        mc = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
        mc.MousePosition = Coord(col, row)
        mc.ButtonState = button #FROM_LEFT_1ST_BUTTON_PRESSED 
        inputs.append(mc)

        if count == 2:
            mc2 = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
            mc2.MousePosition = Coord(col, row)
            mc2.ButtonState = button
            mc2.EventFlags = 2 #double click            
            inputs.append(mc2)

        mc3 = win32console.PyINPUT_RECORDType(win32console.MOUSE_EVENT)
        mc3.MousePosition = Coord(col, row)
        mc3.ButtonState = 0 #release
        inputs.append(mc3)

        self.write_console_input(inputs)
        

    def read(self, full=False, with_colors=False):
        lines = {}
        colors = {}
        buf_info = self._con_out.GetConsoleScreenBufferInfo()
        size = buf_info['Window']
        idx = 0
        for i in range(size.Top, size.Bottom + 1):
            lines[idx] = self._con_out.ReadConsoleOutputCharacter(size.Right+1 - size.Left, Coord(size.Left, i))
            if with_colors:
                colors[idx] = self._con_out.ReadConsoleOutputAttribute(size.Right+1 - size.Left, Coord(size.Left, i))
            idx += 1
        diff_lines = {}
        diff_colors = {}
        last_lines_keys = self._last_lines.keys()
        last_colors_keys = self._last_colors.keys()
        for k, v in lines.items():
            if k in last_colors_keys and self._last_colors[k] != colors[k]:
                diff_colors[k] = colors[k]
            if k in last_lines_keys and self._last_lines[k] == v:
                continue
            diff_lines[k] = v
            diff_colors[k] = colors[k] # if line is changed, then colors need to be reaplied 
        self._last_lines = lines
        self._last_colors = colors

        cursos_position = buf_info['CursorPosition']
        pos = (cursos_position.X, cursos_position.Y)
        if full:
            return lines, pos, colors
        return diff_lines, pos, diff_colors


import socket

UDP_IP="127.0.0.1"
RECV_UDP_PORT=8828
SEND_UDP_PORT=8829

class UdpConsole(object):
    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((UDP_IP, RECV_UDP_PORT))
        self._console = ConsoleServer()

    def run(self):
        while True:
            import json, zlib
            msg = self._sock.recv(2**14)
            response = {"status": "error"}
            try:
                cmd = json.loads(zlib.decompress(msg))
                response["result"] = self.handle_command(cmd)
                response["status"] = "ok"
            except Exception, e:
                response["status"] = "error"
                response["description"] = unicode(e)
            self._sock.sendto(zlib.compress(json.dumps(response)), (UDP_IP, SEND_UDP_PORT))

    def handle_command(self, cmd):
        method = getattr(self._console, cmd["command"])
        return method(*cmd["args"], **cmd["kwds"])


if __name__ == "__main__":
    con = UdpConsole()
    con.run()

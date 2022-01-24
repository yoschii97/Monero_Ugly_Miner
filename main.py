from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty

import socket
import select
import binascii
import struct
import json
import time
import RandomXpy

pool_host = 'cryptonote.social'
pool_port = '5555'
pool_pass = 'xx'
wallet_address = '4B8gXteiaSZ7AsrQBV8nRMXnnUNM2ZtiUYDYmNkjx2DS5CmKptga5cy7VuHshXQo9hML99AkrR7URVVXzCUSMiNN3oJCwK3' \
                 '.MiningDJ '


class InputWindow(Screen):
    # Input Values
    host = ObjectProperty(None)
    port = ObjectProperty(None)
    wallet = ObjectProperty(None)
    testmode = False

    # Callback for the checkbox
    def checkbox_click(self, instance, value):
        if value is True:
            print("Checkbox Checked - Testmode True")
            self.testmode = True
        else:
            print("Checkbox Unchecked - Testmode False")
            self.testmode = False

    # Button Pressed
    def mining_button(self):
        global pool_host, pool_port, wallet_address
        print("Mining Button was pressed.")
        if self.testmode:
            print("Using Default Parameter.")
        else:
            if not self.host.text:
                print("Missing Host!")
                return False
            if not self.port.text:
                print("Missing Port!")
                return False
            if not self.wallet.text:
                print("Missing Wallet!")
                return False
            print("Using Custom Parameter.")
            pool_host = self.host.text
            pool_port = self.port.text
            wallet_address = self.wallet.text

        print("Host: ", pool_host)
        print("Port: ", pool_port)
        print("Wallet: ", wallet_address)
        return True


class Worker:
    global pool_host, pool_port, wallet_address

    def __init__(self, mw):
        self.MiningWindow = mw

    log = ""

    def print(self, msg):
        self.log += msg
        if len(self.log) > 1024:
            self.log = self.log[(len(self.log)-16384):]
        self.MiningWindow.ids.scrollview.text = self.log

    def println(self, msg):
        self.log += msg + '\n'
        if len(self.log) > 1024:
            self.log = self.log[(len(self.log)-16384):]
        self.MiningWindow.ids.scrollview.text = self.log

    def start(self):
        if wallet_address == '4B8gXteiaSZ7AsrQBV8nRMXnnUNM2ZtiUYDYmNkjx2DS5CmKptga5cy7VuHshXQo9hML99AkrR7URVVXzCUSMiNN'\
                             '3oJCwK3.MiningDJ ':
            print("Start Mining with: " + pool_host + ":" + pool_port + "@ as Support, Thx.")
            self.println("Start Mining with: " + pool_host + ":" + pool_port + "@ as Support, Thx.")
        else:
            print("Start Mining with: " + pool_host + ":" + pool_port + "@" + wallet_address)
            self.println("Start Mining with: " + pool_host + ":" + pool_port + "@" + wallet_address)
        self.login()
        print("Schedule: read_socket")
        Clock.schedule_interval(self.read_socket_continuously, 0)
        print("Schedule: worker")
        Clock.schedule_interval(self.worker, 0)

    socket_ = socket.socket()
    socket_.setblocking(False)

    def stop(self):
        self.socket_.close()
        Clock.unschedule(self.worker)
        Clock.unschedule(self.read_socket_continuously)

    def login(self):
        pool_ip = socket.gethostbyname(pool_host)
        print("Pool IP-Addresse: " + pool_ip)
        self.socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket_.connect((pool_ip, int(pool_port)))
            print("Connection with Pool successful!")
            self.println("Connection with Pool successful!")
        except TimeoutError:
            print("Error! Connection with Pool unsuccessful!")
            self.println("Error! Connection with Pool unsuccessful!")
            return False

        print('Logging into pool: {}:{}'.format(pool_host, pool_port))
        self.println('Logging into pool: {}:{}'.format(pool_host, pool_port))

        login_json = {
            'method': 'login',
            'params': {
                'login': wallet_address,
                'pass': pool_pass,
                'rigid': '',
                'agent': 'ProtocolTest/0.1'
            },
            'id': 1
        }
        self.socket_.sendall(str(json.dumps(login_json) + '\n').encode('utf-8'))
        select.select([self.socket_], [], [], 3)

    q = None
    log_id = ''

    def read_socket_continuously(self, dt):
        ready = select.select([self.socket_], [], [], 0)
        if not ready[0]:
            return
        line = self.socket_.makefile().readline()
        r = json.loads(line)
        print(r)
        error = r.get('error')
        result = r.get('result')
        method = r.get('method')
        params = r.get('params')
        if error:
            print('Error: {}'.format(error))
            self.println('Error: {}'.format(error))
            return
        if result and result.get('status'):
            print('Status: {}'.format(result.get('status')))
            self.println('Status: {}'.format(result.get('status')))
            print(time.ctime())
            self.println(time.ctime())
            print("Waiting for new job ...")
            self.println("Waiting for new job ...")
        if result and result.get('job'):
            self.log_id = result.get('id')
            print('Login ID: ' + self.log_id)
            self.println('Login ID: ' + self.log_id)
            job = result.get('job')
            job['login_id'] = self.log_id
            self.q = job
        elif method and method == 'job' and len(self.log_id):
            self.q = params

    def pack_nonce(self, blob, nonce):
        b = binascii.unhexlify(blob)
        bin = struct.pack('39B', *bytearray(b[:39]))
        bin += struct.pack('I', nonce)
        bin += struct.pack('{}B'.format(len(b) - 43), *bytearray(b[43:]))
        return bin

    mining = False
    job = login_id = blob = target = job_id = height = seed_hash = nonce = started = hash_count = None

    def worker(self, dt):
        if not self.mining:
            if not self.q:
                return
            job = self.q
            self.q = None
            if job.get('login_id'):
                self.login_id = job.get('login_id')
            self.blob = job.get('blob')
            self.target = job.get('target')
            self.job_id = job.get('job_id')
            self.height = job.get('height')
            self.seed_hash = binascii.unhexlify(job.get('seed_hash'))
            print('New job with target: {}, RandomX, height: {}'.format(self.target, self.height))
            self.println('New job with target: {}, RandomX, height: {}'.format(self.target, self.height))
            self.target = struct.unpack('I', binascii.unhexlify(self.target))[0]
            if self.target >> 32 == 0:
                self.target = int(0xFFFFFFFFFFFFFFFF / int(0xFFFFFFFF / self.target))
            self.nonce = 1
            print("Start calculate hashes ")
            self.print("Start calculate hashes ")
            self.started = time.time()
            self.hash_count = 0
            self.mining = True
        for x in range(2):
            if self.q:
                self.println(" ")
                self.println("Got new Job, discard old. Risk of stale.")
                self.mining = False
                break
            bin = self.pack_nonce(self.blob, self.nonce)
            hash = RandomXpy.get_rx_hash(bin, self.seed_hash, self.height)
            self.hash_count += 1
            if not self.hash_count % 20:
                self.print(".")
            hex_hash = binascii.hexlify(hash).decode()
            r64 = struct.unpack('Q', hash[24:])[0]
            if r64 < self.target:
                self.println(" ")
                elapsed = time.time() - self.started
                hr = int(self.hash_count / elapsed)
                print("Hashrate: ", hr, " H/s")
                self.println("Hashrate {}".format(str(hr)) + " H/s")
                submit_json = {
                    'method': 'submit',
                    'params': {
                        'id': self.login_id,
                        'job_id': self.job_id,
                        'nonce': binascii.hexlify(struct.pack('<I', self.nonce)).decode(),
                        'result': hex_hash
                    },
                    'id': 1
                }
                print('Submitting hash: {}'.format(hex_hash))
    #           self.println('Submitting hash: {}'.format(hex_hash))
                self.socket_.sendall(str(json.dumps(submit_json) + '\n').encode('utf-8'))
                select.select([self.socket_], [], [], 3)
                self.mining = False
                break
            self.nonce += 1


class MiningWindow(Screen):
    scrollview = ObjectProperty(None)

    def _println(self, msg):
        self.scrollview.text += msg + '\n'


class WindowManager(ScreenManager):
    pass


Builder.load_file("layout.kv")
sm = WindowManager()
iw = InputWindow()
mw = MiningWindow()
sm.add_widget(iw)
sm.add_widget(mw)


class Miner(App):
    def build(self):
        return sm

    worker = Worker(mw)

    def start_mining(self):
        print("Miner.start")
        self.worker.start()

    def stop_mining(self):
        print("Miner.stop")
        self.worker.stop()


if __name__ == "__main__":
    Miner().run()

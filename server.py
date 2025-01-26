## server.py
import socket
import struct
import random
import threading
import time


base = 0
next_seq_num = 0
window = {}


def unreliableSend(packet, sock, userIP, errRate):
    if errRate < random.randint(0, 100):
        sock.sendto(packet, userIP)

def create_packet(packet_type, seq_num, payload=b""):
    return struct.pack("!BB", packet_type, seq_num) + payload

def create_data_packet(packet_type, data_len=0 , seq_num=0, payload=b""):
    return struct.pack("!BBB", packet_type, data_len ,seq_num) + payload

def server(port, filename, err_rate, window_size):
    global base
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.settimeout(10)
    server_socket.bind(("", port))
    
    # Handling handshake
    try:
        data, client_addr = server_socket.recvfrom(1024)
        print("Received handshake packet from:", client_addr)
        if data[0] == 0 and data[2:].decode() == filename:
            ack_packet = create_packet(1, 0)
            print("Sending ACK for handshake")
            unreliableSend(ack_packet, server_socket, client_addr, 0)
            try:
                request = server_socket.recvfrom(1024)
                if request:
                    print("Handshake successful")
            except socket.timeout:
                print("Handshake timeout, closing server.")
                server_socket.close()
                return
        else:
            print("Wrong file name, handshake failed")
            server_socket.close()
            return
    except socket.timeout:
        print("Handshake timeout, closing server.")
        server_socket.close()
        return
    
    # Sending file data with Selective Repeat
    with open(filename, "r") as file:
        lines = file.readlines()
    
    
    
    lock = threading.Lock()
    event = threading.Event()

    def retransmit():
        global base, next_seq_num, window
        while base < len(lines):
            time.sleep(0.1)
            with lock:
                for i in range(base, min(base + window_size, len(lines))):
                    if i in window and not window[i][0] and time.time() - window[i][1] > 0.1:
                        print(f"Packet {i} timed out. Retransmitting packet {i}")
                        data = lines[i]
                        data_packet = create_data_packet(2, len(data), i, data.encode())
                        unreliableSend(data_packet, server_socket, client_addr, err_rate)
                        window[i] = (False, time.time())
                    if i not in window:
                        print(f"Sending packet {i}")
                        data = lines[i]
                        data_packet = create_data_packet(2, len(data), i, data.encode())
                        unreliableSend(data_packet, server_socket, client_addr, err_rate)
                        window[i] = (False, time.time())
                next_seq_num =  min(base + window_size, len(lines))
            

    

    def initial_transmit():
        global base, next_seq_num, window
        with lock:
            for i in range(base, min(base + window_size, len(lines))):
                data = lines[i]
                print(f"Sending packet {i}")
                data_packet = create_data_packet(2, len(data), i, data.encode())
                unreliableSend(data_packet, server_socket, client_addr, err_rate)
                window[i] = (False, time.time())
            next_seq_num =  min(base + window_size, len(lines))

    def handle_ack():
        global base, next_seq_num, window
        while base < len(lines):
            
                try:
                    ack, _ = server_socket.recvfrom(1024)
                    if ack[0] == 1:
                        print(f"Received ACK for packet {ack[1]}")
                        with lock:
                            if ack[1] in window:
                                window[ack[1]] = (True, window[ack[1]][1])
                            if ack[1] == base:
                                filtered_keys = [key for key, value in window.items() if not value[0]]
                                if filtered_keys:
                                    base = min(filtered_keys)
                                elif next_seq_num != len(lines):
                                    base = next_seq_num
                                elif next_seq_num == len(lines):
                                    base = len(lines)                           
                                all_keys = set(window.keys())
                                true_keys = all_keys - set(filtered_keys)
                                for key in true_keys:
                                    del window[key]
                            
                                
                except socket.timeout:
                    pass
        





    initial_transmit()
    threading.Thread(target=retransmit, daemon=True).start()
    threading.Thread(target=handle_ack, daemon=True).start()
    
    while base < len(lines):
        time.sleep(0.1)  
    
    


    # Sending FIN packet
    fin_packet = create_packet(3, base)
    unreliableSend(fin_packet, server_socket, client_addr, err_rate)
    print("Sent FIN packet, waiting for ACK...")

    try:
        ack, _ = server_socket.recvfrom(1024)
        if ack[0] == 1 and ack[1] == base:
            print("Client acknowledged FIN, waiting for final FIN...")
            try:
                fin, _ = server_socket.recvfrom(1024)
                if fin[0] == 3 and fin[1] == base + 1:
                    print("Final FIN received, closing server.")
                    final_ack = create_packet(1, base + 1)
                    unreliableSend(final_ack, server_socket, client_addr, err_rate)
                    server_socket.close()
                    return
            except socket.timeout:
                print("Timeout waiting for final FIN, closing server.")
                server_socket.close()
                return
            
        else:
            print("Unexpected ACK received, closing server.")
            server_socket.close()
            return
    except socket.error:
        print("Timeout waiting for FIN ACK, closing server.")
        
    server_socket.close()

if __name__ == "__main__":
    import sys
    server(12345, "testfile.txt", 20, 3)

## client.py
import socket
import struct
import random

#If a valid error rate is entered by the user, the packet is sent with the error rate via UDP protocol.
def unreliableSend(packet, sock, userIP, errRate):
    if errRate < random.randint(0, 100):
        sock.sendto(packet, userIP)
        
#The packet is created with the given packet type, sequence number and payload. First two bytes are the packet type and sequence number, the rest is the payload.
def create_packet(packet_type, seq_num=0, payload=b""):
    return struct.pack("!BB", packet_type, seq_num) + payload

#Create a client socket and send the handshake packet to the server. If the handshake is successful, the client receives the data packets and sends the ACK packets to the server.
def client(server_ip, server_port, filename, err_rate):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set timeout for the client socket (In case of no return to the client)
    client_socket.settimeout(2)

    # Triple Handshake, it terminates the socket if the handshake is not successful
    def initiate_handshake():
        handshake_packet = create_packet(0, 0, filename.encode())
        unreliableSend(handshake_packet, client_socket, (server_ip, server_port), 0)
        print("Sent handshake packet to server")
        try:
            data, _ = client_socket.recvfrom(1024)
            print("Recieved handshake ACK from server")
            if data[0] == 1:
                print("Handshake successful, sending final ACK for handshake")
                unreliableSend(data, client_socket, (server_ip, server_port), 0)
            else:
                print("Handshake failed")
                client_socket.close()
                return
        except socket.timeout:
            print("Handshake timeout, closing client")
            client_socket.close()
            return

    initiate_handshake()
    # Receiving data using Selective Repeat
    received_packets = {}
    expected_seq_num = 0
    #Until break is used it listens for the packets from the server. If the packet is a data packet, it sends an ACK packet to the server. If the packet is a FIN packet, it sends a FIN ACK and FIN packet to the server.
    while True:
        try:
            data, _ = client_socket.recvfrom(1024)
            packet_type = data[0]
            
            if packet_type == 2:
                seq_num = data[2]
                received_packets[seq_num] = data[3:].decode()
                ack_packet = create_packet(1, seq_num)
                unreliableSend(ack_packet, client_socket, (server_ip, server_port), err_rate)

                while expected_seq_num in received_packets:
                    print("Received:", str(received_packets.pop(expected_seq_num)).strip())
                    expected_seq_num += 1
                    
            if packet_type == 3:
                print("Received FIN packet")
                fin_ack = create_packet(1, seq_num + 1)
                fin_packet = create_packet(3, seq_num + 2)
                print("Sending FIN ACK and FIN packet to server")
                unreliableSend(fin_ack, client_socket, (server_ip, server_port), err_rate)
                try:
                    unreliableSend(fin_packet, client_socket, (server_ip, server_port), err_rate)
                    try:
                        data, _ = client_socket.recvfrom(1024)
                        if data[0] == 3:
                            print("Received final ACK from server")
                            break
                    except socket.timeout:
                        print("FIN ACK timeout")
                        client_socket.close()
                        return
                except socket.error:
                    print("Server closed connection")
                    break
        except socket.timeout:
            print("Timeout")
            break
    print("Closing connection")
    client_socket.close()

if __name__ == "__main__":
    while True:
        fileName = input("Enter the file name: ")
        errorRate = int(input("Enter the error rate: "))
        client("localhost", 12345, fileName, errorRate)
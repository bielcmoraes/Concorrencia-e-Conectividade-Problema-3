import socket
import threading
import os
import platform
import json
import time
import uuid
from queue import Queue
from lamport_clock import LamportClock

port = 5555
# peer_addresses = [("172.16.103.1", port), ("172.16.103.2", port), ("172.16.103.3", port), ("172.16.103.4", port), ("172.16.103.5", port), ("172.16.103.6", port), ("172.16.103.7", port), ("172.16.103.8", port), ("172.16.103.9", port), ("172.16.103.10", port), ("172.16.103.11", port), ("172.16.103.12", port), ("172.16.103.13", port), ("172.16.103.14", port)]
peer_addresses = [("192.168.43.198", port), ("192.168.43.107", port)]
peer_addresses_online = []
peer_status = {}
acks = {}
pongs = Queue()
received_packets = Queue()
lamport_clock = LamportClock()
my_info = (None, port)
all_messages = []
confirmed_messages = []
mutex = threading.Lock()

OPERATION_NUMBER = 5

# Função para verificar se um par está online ou offline
def send_ping(peer_address):
    try:
        message_data = {
            "message_type": "Ping",
            "id": str(uuid.uuid4())
        }
        message_json = json.dumps(message_data)
        encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
        send_for_all(encrypted_message)

        peer_on_exists = peer_status.get(peer_address[0])
                    
        if not peer_on_exists:
            peer_status[peer_address[0]] = [message_data["id"]]
            
        else:
            peer_status[peer_address[0]].append(message_data["id"])

    except socket.timeout:
        pass
    except Exception as e:
        print(f"Erro ao verificar o status do par {peer_address}: {e}")

def send_all_ping():
    while True:
        for peer_address in peer_addresses:
            if peer_address != my_info:
                send_ping(peer_address)
        time.sleep(1)  # Verificar o status dos pares a cada 5 segundos

def check_status():
    while True:
        pong = pongs.get()
        addr = pong[0]
        message = pong[1]
        id = message["id"]

        try:
            
            if (addr[0], port) not in peer_addresses_online:
                peer_addresses_online.append((addr[0], port)) # Adiciona na lista de usuários online

            peer_status[addr[0]].remove(id)

            if len(peer_status[addr[0]]) > 3:
                peer_status.pop(addr[0]) #Remove o status online
                peer_addresses_online.remove((addr[0], port)) #Remove da lista de online
        except (KeyError, ValueError):
            pass
        
        time.sleep(1)
        # print("Pares Online:", peer_addresses_online)

def remove_pending_messages():

    while True:
        for message_id, acks_list in list(acks.items()):
            all_confirmed = all(addr_id[0] in peer_status for addr_id in acks_list) #Verificar se os pares online confirmaram o recebimento da mensagem

            if all_confirmed:
                confirmed_data = {
                    "message_type": "Confirmed",
                    "message_id": message_id
                }
                confirmed_json = json.dumps(confirmed_data)
                encrypted_confirmed = encrypt_message(confirmed_json, OPERATION_NUMBER)
                send_for_online(encrypted_confirmed)
                
                list_temp = []
                for message in all_messages:
                    id = message[1]["message_id"]
                    if str(message_id) == str(id) and message not in confirmed_messages:
                        confirmed_messages.append(message) # Adiciona a mensagem à lista de mensagens confirmadas
                        # all_messages.remove(message) # Remove a mensagem da lista de mensagens não confirmadas               
                        list_temp.append(message)
                
                for text in list_temp:
                    all_messages.remove(text)

# Função para sincronizar mensagens
def start_sync():

    # Gere um novo ID de mensagem
    message_id = lamport_clock.get_time()

    # Crie um dicionário para a mensagem em formato JSON
    message_data = {
        "message_type": "Sync",
        "message_id": [my_info[0], message_id],
        "text": "Start sync."
    }

    # Serializar a mensagem em JSON
    message_json = json.dumps(message_data)

    encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
    # Enviar a mensagem para todos os pares
    send_for_online(encrypted_message)

# Função para solicitar sincronização a cada "X" tempo
def time_sync():
    while True:
        start_sync()
        time.sleep(5)

def encrypt_message(frase, port):
    mensagem = ""
    for i in frase:
        mensagem += chr (ord(i) + port)
    return mensagem

def decrypt_message(mensagem, port):
    frase = ""
    for i in mensagem:
        frase += chr (ord(i) - port)
    return frase

def receive_messages():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    udp_socket.bind(my_info)

    try:
        while True:
            data, addr = udp_socket.recvfrom(2048)
            received_packets.put((addr, data))
    finally:
        udp_socket.close()

def send_for_all(objMsg):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for peer_addr in peer_addresses:
            if peer_addr != my_info:
                    client_socket.sendto(objMsg.encode(), peer_addr)
        
    except Exception as e:
        print("Erro ao enviar pacote: ", e)
    finally:
        client_socket.close()

def send_for_online(objMsg):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for peer_addr in peer_addresses_online:
            if peer_addr != my_info:
                    client_socket.sendto(objMsg.encode(), peer_addr)
                    #time.sleep(1)
    except Exception as e:
        print("Erro ao enviar pacote: ", e)
    finally:
        client_socket.close()

def send_for_one(objMsg, peer_addr):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if peer_addr != my_info:
            client_socket.sendto(objMsg.encode(), peer_addr)

    except Exception as e:
        print("Erro ao enviar pacote: ", e)
    finally:
        client_socket.close()

def send_messages():
    while True:
        message_text = input("Digite as mensagens (ou 'exit' para sair): ")

        if message_text.lower() == 'exit':
            break

        # Gere um novo ID de mensagem
        message_id = lamport_clock.get_time()

        # Crie um dicionário para a mensagem em formato JSON
        message_data = {
            "message_type": "Message",
            "message_id": [my_info[0], message_id],
            "text": message_text,
            "ack_requested": True
        }

        # Serializar a mensagem em JSON
        message_json = json.dumps(message_data)

        # Enviar a mensagem para todos os pares
        
        encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
        if encrypted_message:
            send_for_online(encrypted_message)

        message_save = (my_info[0], message_data)
        if message_save not in all_messages:
            all_messages.append(message_save)
            lamport_clock.increment()

def order_packages():
    while True:
        package_received = received_packets.get()
        addr = package_received[0]
        data = package_received[1]

        try:
            data_decrypt = decrypt_message(data.decode("utf-8"), OPERATION_NUMBER)

            if data_decrypt:
                message_data = json.loads(data_decrypt)
                
                if "message_type" in message_data:
                    message_type = message_data["message_type"]
                    
                    if message_type == "Ping":
                        
                        message_data = {
                            "message_type": "Pong",
                            "id": message_data["id"]
                        }

                        message_json = json.dumps(message_data)

                        encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
                        send_for_one(encrypted_message, (addr[0], port))

                    elif message_type == "Pong":
                        pongs.put((addr, message_data))

                    elif message_type == "Message":
                        print("Message")

                        if "message_id" in message_data and "text" in message_data and "ack_requested" in message_data:
                            message_id = message_data["message_id"]
                            ack_requested = message_data["ack_requested"]

                            if ack_requested:
                                if ((message_id[0], message_data)) not in all_messages:
                                    all_messages.append((message_id[0], message_data))
                                    lamport_clock.update(message_id[1])
                            
                                ack_data = {
                                    "message_type": "Ack",
                                    "message_id": message_id
                                }
                                ack_json = json.dumps(ack_data)
                                encrypted_ack = encrypt_message(ack_json, OPERATION_NUMBER)
                                send_for_one(encrypted_ack, (addr[0], port))
                            
                            else:
                                if message not in confirmed_messages:
                                    confirmed_messages.append((message_id[0], message_data)) # Adiciona as mensagens que são provenientes de sincronização direto na lista de mensagens confirmadas (pressupondo que os pares online tenham essas mensagens)
                                    lamport_clock.update(message_id[1])
                    
                    elif message_type == "Ack":
                        print("ACK")
                        if "message_id" in message_data:
                            message_id = message_data["message_id"]
                            
                            ack_key_exists = acks.get(str(message_id))
                        
                            if not ack_key_exists:
                                acks[str(message_id)] = [addr]
                                
                            else:
                                acks[str(message_id)].append(addr)
                    
                    elif message_type == "Confirmed":
                        
                        for message in all_messages:
                            confirmed_id = message_data["message_id"]
                            message_id = message[1]["message_id"]

                            if str(confirmed_id) == str(message_id) and message not in confirmed_messages:
                                print("Confirmed")
                                confirmed_messages.append(message) # Adiciona a mensagem à lista de mensagens confirmadas
                                all_messages.remove(message) # Remove a mensagem da lista de mensagens não confirmadas
                                break
                                    
                    elif message_type == "Sync":
                        print("Sync")
                        if "message_id" in message_data and "text" in message_data:
                            text_sync = message_data["text"]
                            if "Start sync" in text_sync:
                                for message in confirmed_messages:
                                    message[1]["ack_requested"] = False # Altera o status para permitir que essas mensagens sejam adicionadas diretamente na lista de mensagens confirmadas
                                    message_json = json.dumps(message[1])
                                    message_encrypted = encrypt_message(message_json, OPERATION_NUMBER)
                                    send_for_one(message_encrypted, (addr[0], port))
        except Exception as e:
            print("Erro ao ordenar pacotes: ", e)

def order_messages(messages):
    # Utilize a função sorted do Python, fornecendo a função de ordenação com base no carimbo de tempo e, em caso de empate, no maior valor em messages[0]
    ordered_messages = sorted(messages, key=lambda x: (x[1]["message_id"][1], x[0]))
    return ordered_messages

def read_messages():
    
    all_messages_sorted = order_messages(confirmed_messages)
    print("\nTodas as mensagens: ")
    for message_data in all_messages_sorted:
        address = message_data[0]
        text = message_data[1]['text']
        message_id = message_data[1]['message_id']
        if address == my_info:
            print(f"My message({message_id}): {text}")
        else:
            print(f"{address}({message_id}): {text}") 
    print()

# Função para limpar o terminal independente do S.O
def clear_terminal():
    current_os = platform.system()
    if current_os == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def main():
    global my_info

    my_ip = input("Digite seu endereço IP: ")
    my_info = (my_ip, port)

    try:
            
            # Iniciar a thread para receber mensagens 
            receive_thread = threading.Thread(target=receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            order_packages_thread = threading.Thread(target=order_packages)
            order_packages_thread.daemon = True
            order_packages_thread.start()

            send_ping_thread = threading.Thread(target=send_all_ping)
            send_ping_thread.daemon = True
            send_ping_thread.start()

            check_status_thread = threading.Thread(target=check_status)
            check_status_thread.daemon = True
            check_status_thread.start()

            remove_pending_messages_thread = threading.Thread(target=remove_pending_messages)
            remove_pending_messages_thread.daemon = True
            remove_pending_messages_thread.start()

            start_sync()
            # clear_terminal()

            while True:
                print("[1] Para enviar mensagens")
                print("[2] Para visualizar mensagens")
                print("[3] Para sair")

                menu_main = int(input())

                if menu_main == 1:
                    # Inicie a função send_messages na thread principal
                    send_messages()
                    # clear_terminal()

                elif menu_main == 2:
                    read_messages()

                elif menu_main == 3:
                    # Feche o socket ao sair                    
                    print("---Encerrando conexões---")
                    exit()
    except socket.timeout:
        pass

if __name__ == "__main__":
    main()
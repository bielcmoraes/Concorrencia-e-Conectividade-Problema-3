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

peer_addresses = [("172.16.103.1", port), ("172.16.103.2", port), ("172.16.103.3", port), ("172.16.103.4", port), ("172.16.103.5", port), ("172.16.103.6", port), ("172.16.103.7", port), ("172.16.103.8", port), ("172.16.103.9", port), ("172.16.103.10", port), ("172.16.103.11", port), ("172.16.103.12", port), ("172.16.103.13", port), ("172.16.103.14", port), ("192.168.43.198", port), ("192.168.43.107", port), ("192.168.0.121", port), ("192.168.0.111", port)]

peer_status = {
    ("192.168.0.121", port): {"Status": False, "Time_stamp": 0},
    ("192.168.0.111", port): {"Status": False, "Time_stamp": 0},
    ("192.168.43.198", port): {"Status": False, "Time_stamp": 0},
    ("192.168.43.107", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.1", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.2", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.3", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.4", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.5", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.6", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.7", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.8", port): {"Status": False, "Time_stamp": 0},
    ("172.16.103.9", port): {"Status": False, "Time_stamp": 0},
}
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
        send_for_one(encrypted_message, peer_address)
    except socket.timeout:
        pass
    except Exception as e:
        print(f"Erro ao verificar o status do par {peer_address}: {e}")

def send_all_ping():
    while True:
        for peer_address in peer_addresses:
            if peer_address != my_info:
                send_ping(peer_address)
        time.sleep(0.5)  # Verificar o status dos pares a cada 5 segundos

def check_status():

    while True:
        for peer in peer_status:
            peer_time_stemp = peer_status.get(peer).get("Time_stamp")
            if (time.time() - peer_time_stemp) > 4:
                peer_status[peer]["Status"] = False
            
            if peer == my_info:
                peer_status[my_info]["Status"] = True
        
        time.sleep(0.2)

def compare_ip_lists(list1, list2):
    # Extrai apenas os endereços IP da primeira lista
    if list1:
        ips_list1 = [ip_port[0] for ip_port in list1]
    if list2:
        ips_list2 = [ip_port[0] for ip_port in list2]
        # Verifica se todos os endereços IP da segunda lista estão presentes na primeira lista
        for ip in ips_list2:
            if ip not in ips_list1:
                return False

    return True

def remove_pending_messages():

    while True:

        list_temp = []
        for info in all_messages:
            message = info[1]
            message_id = message["message_id"]
            senders_exits = message.get("Senders")

            if senders_exits == []:
                if len(senders_exits) == 0 and message not in confirmed_messages:
                    confirmed_messages.append(message)
                    list_temp.append(info)
                    
            else:
                acks_list = acks.get(str(message_id))
                all_confirmed = compare_ip_lists(senders_exits, acks_list)
                if all_confirmed == True and message not in confirmed_messages:

                    confirmed_data = {
                    "message_type": "Confirmed",
                    "message_id": message_id
                    }
                    confirmed_json = json.dumps(confirmed_data)
                    encrypted_confirmed = encrypt_message(confirmed_json, OPERATION_NUMBER)
                    send_for_online(encrypted_confirmed)
                    confirmed_messages.append(message)
                    list_temp.append(info)

        for info in list_temp:
            all_messages.remove(info)
        
        time.sleep(0.5)

# Função para sincronizar mensagens
def start_sync():

    print("Sincronizando...")

    # Gere um novo ID de mensagem
    message_id = lamport_clock.get_time()

    # Crie um dicionário para a mensagem em formato JSON
    message_data = {
        "message_type": "Sync",
        "message_id": [my_info[0], message_id]
    }

    # Serializar a mensagem em JSON
    message_json = json.dumps(message_data)

    encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
    # Enviar a mensagem para todos os pares
    time.sleep(1)
    send_for_online(encrypted_message)
    time.sleep(10)

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
        senders = []
        for peer_addr in peer_addresses:
            if peer_addr in peer_status:
                status_peer = peer_status.get(peer_addr).get("Status")
                if status_peer and peer_addr != my_info and status_peer == True:
                    client_socket.sendto(objMsg.encode(), peer_addr)
                    senders.append(peer_addr)
                    # time.sleep(0.4)
        
        return senders
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

        if message_text.lower() == "exit":
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
            senders = send_for_online(encrypted_message)

        message_data["Senders"] = senders
        message_save = (my_info[0], message_data)

        if message_save not in all_messages:
            all_messages.append(message_save)
            lamport_clock.increment()

def send_messages_bot():
    while True:
        message_text = input("Digite as mensagens (ou 'exit' para sair): ")
        
        try:
            if message_text != "exit":
                for i in range(1, 500):  # Envia 20 mensagens sequenciais
                    message_text = f"Mensagem {i}"  # Mensagem sequencial
                    
                    # Gera um novo ID de mensagem
                    message_id = lamport_clock.get_time()

                    # Cria um dicionário para a mensagem em formato JSON
                    message_data = {
                        "message_type": "Message",
                        "message_id": [my_info[0], message_id],
                        "text": message_text,
                        "ack_requested": True
                    }

                    # Serializa a mensagem em JSON
                    message_json = json.dumps(message_data)

                    # Envia a mensagem para todos os pares
                    encrypted_message = encrypt_message(message_json, OPERATION_NUMBER)
                    if encrypted_message:
                        senders = send_for_online(encrypted_message)

                    message_data["Senders"] = senders
                    message_save = (my_info[0], message_data)

                    if message_save not in all_messages:
                        all_messages.append(message_save)
                        lamport_clock.increment()
                    
                    # Aguarda um pequeno intervalo antes de enviar a próxima mensagem
                    time.sleep(0.3)
                
                return

        except Exception as e:
            print("Erro ao enviar mensagens:", e)

def order_packages():
    while True:
        package_received = received_packets.get()
        addr = package_received[0]
        data = package_received[1]

        # try:
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
                    peer_status[(addr[0], port)]["Status"] = True
                    peer_status[(addr[0], port)]["Time_stamp"] = time.time()

                elif message_type == "Message":

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
                            message_data["ack_requested"] = True
                            print(message_data)
                            print(confirmed_messages)
                            if message_data not in confirmed_messages:
                                confirmed_messages.append(message_data) # Adiciona as mensagens que são provenientes de sincronização direto na lista de mensagens confirmadas (pressupondo que os pares online tenham essas mensagens)
                                lamport_clock.update(message_id[1])
                
                elif message_type == "Ack":
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
                            
                            confirmed_messages.append(message[1]) # Adiciona a mensagem à lista de mensagens confirmadas

                            if (message_id[0], message_data) in all_messages:
                                all_messages.remove(message) # Remove a mensagem da lista de mensagens não confirmadas
                                
                elif message_type == "Sync":
                    if "message_id" in message_data:
                        for message in confirmed_messages:
                            print(message)
                            message_sync = message # Altera o status para permitir que essas mensagens sejam adicionadas diretamente na lista de mensagens confirmadas
                            message_sync["ack_requested"] = False
                            message_json = json.dumps(message_sync)
                            message_encrypted = encrypt_message(message_json, OPERATION_NUMBER)
                            send_for_one(message_encrypted, (addr[0], port))
        # except Exception as e:
        #     print("Erro ao ordenar pacotes: ", e)

def key_function(message):
    message_id = message["message_id"]
    second_value = message_id[1] if isinstance(message_id, tuple) and len(message_id) >= 2 else 0
    first_value = message_id[0] if isinstance(message_id, tuple) else 0
    return (second_value, first_value)

def order_messages(messages):
    try:
        sorted_messages = sorted(messages, key=key_function)
        return sorted_messages
    except Exception as e:
        print("Erro ao ordenar mensagens:", e)
        return []

def read_messages():
    all_messages_sorted = order_messages(confirmed_messages)
    print("\nTodas as mensagens: ")
    print(all_messages_sorted)
    print(confirmed_messages)
    for message_data in all_messages_sorted:
        address = (message_data["message_id"][0], port)
        text = message_data["text"]
        message_id = message_data["message_id"][1]
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

def get_local_ip():
    try:
        # Obtém o nome do host da máquina
        hostname = socket.gethostname()

        # Obtém o endereço IP correspondente ao nome do host
        ip_address = socket.gethostbyname(hostname)

        return ip_address
    except Exception as e:
        print("Erro ao obter endereço IP local:", e)
        return None

def main():
    global my_info
    

    my_ip = get_local_ip()
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
            
            start_sync()

            remove_pending_messages_thread = threading.Thread(target=remove_pending_messages)
            remove_pending_messages_thread.daemon = True
            remove_pending_messages_thread.start()

            # clear_terminal()

            while True:
                print("[1] Para enviar mensagens")
                print("[2] Para visualizar mensagens")
                print("[3] Para sair")

                menu_main = int(input())

                if menu_main == 1:
                    # Inicie a função send_messages na thread principal
                    send_messages()
                    # send_messages_bot()
                    # clear_terminal()

                elif menu_main == 2:
                    read_messages()
                    # print(confirmed_messages)

                elif menu_main == 3:
                    # Feche o socket ao sair                    
                    print("---Encerrando conexões---")
                    exit()
    except socket.timeout:
        pass

if __name__ == "__main__":
    main()
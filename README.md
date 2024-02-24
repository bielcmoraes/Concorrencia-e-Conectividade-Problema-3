<div align="center">
  <h1>
      Relatório do problema 3: ZapsZap Release Candidate
  </h1>

  <h3>
    Gabriel Cordeiro Moraes
  </h3>

  <p>
    Engenharia de Computação – Universidade Estadual de Feira de Santana (UEFS)
    Av. Transnordestina, s/n, Novo Horizonte
    Feira de Santana – BA, Brasil – 44036-900
  </p>

  <center>gcmorais66@gmail.com</center>

</div>

# 1. Introdução

Os aplicativos de mensagens desempenham um papel fundamental no ambiente corporativo, transformando a forma como as organizações se comunicam e colaboram. Em um mundo empresarial cada vez mais dinâmico e globalizado, a capacidade de trocar informações de maneira rápida e eficiente é crucial para o sucesso de qualquer empreendimento. Os aplicativos de mensagens oferecem uma plataforma instantânea para a comunicação, quebrando as barreiras de tempo e espaço, permitindo que equipes se conectem instantaneamente, independentemente da localização geográfica.

No problema 2, uma startup decidiu desenvolver um novo software de mensagens instantâneas voltado para o mercado corporativo e baseado no modelo peer-to-peer (P2P). O protótipo dessa solução deve oferecer um serviço descentralizado, sem uso de servidor central e que permita a troca de mensagens de texto entre grupos de usuários de uma empresa. Além de garantir a comunicação segura através de chaves criptográficas.

O produto em forma de software foi desenvolvido utilizando a linguagem de programação Python na versão 3.11, além das bibliotecas fornecidas pelo própio pacote da linguagem, entre elas: socket, threading, queue, time, os, entre outras. Por fim, o software foi buildado em container Docker para garantir a estabilidade e praticidade. O conjunto de escolhas e decisões tomadas neste projeto resultaram em um sistema simples, porém eficiente e capaz de atender às demandas e exigências principais da startup contratante.

Embora o protótipo da solução anterior tenha obtido relativo sucesso, o desafio para desenvolver um novo software de mensagens instantâneas baseado no modelo P2P continua neste problema. Um ponto que deve ser considerado nesta versão é que o sistema deve realmente prover um serviço confiável em que, se uma mensagem for exibida na interface de um determinado usuário, deve também ser exibida na interface dos outros usuários.

# 2. Metodologia

### 2.1 - Sincronização
A sincronização em sistemas distribuídos representa um elemento-chave para garantir a coerência e a consistência das operações em ambientes onde múltiplos dispositivos ou servidores interagem. Em tais sistemas, onde a computação ocorre em diferentes locais geográficos/máquinas ou em várias instâncias, a sincronização se torna imperativa para evitar conflitos e assegurar que as informações estejam atualizadas e alinhadas entre os diversos pontos da rede. Por esse motivo, optou-se pela utilização de utilização de relógios lógicos, visto que oferecem diversos pontos positivos que contribuem para uma sincronização mais eficaz e coerente entre os diferentes componentes.

Diantes de algumas opções disponiveis para a implementação do relógio lógico, o algoritmo de Lamporte foi o escolhido pois este relógio lógico não se baseia em tempo absoluto, mas sim em uma contagem local de eventos ocorridos em cada processo. Cada evento é marcado com um carimbo de tempo lógico, representando a relação causal entre eventos em diferentes nodos. Assim, a ordenação das mensagens se deu por meio do timestamp do relógio combinado com o endereço IP do remetente da mensagem.

### 2.2 - Pacotes
Para que o sistema funcionasse de forma adequada, 6 tipos de pacotes foram estabelecidos:

1. **Pacote de mensagem**: { "message_type": "Message", "message_id": [ip_sender, current_timestamp], "text": ‘ ’, "ack_requested": Boolean }

   * message_type: string que identifica o tipo de pacote.
   * message_id: lista com o endereço IP do remetente da mensagem e o timestamp atual responsavel por identificar unicamente o pacote.
   * text: texto da mensagem que foi enviada. (Área de dados do pacote)
   * ack_requested: Booleano indicando se a mensagem precisa d confirmação.

2. **Solicitação de sincronização**: { "message_type": "Sync", "message_id": [ip_sender, current_timestamp] }

   * message_type: string que identifica o tipo de pacote.
   * message_id: lista com o endereço IP do remetente da mensagem e o timestamp atual responsavel por identificar unicamente o pacote.
   * text: texto informando que é uma solicitação de sincronização. (Área de dados do pacote)

3. **Verificação de pares ativos**: { "message_type": "Ping", "id": str(uuid.uuid4()) }

  * message_type: string que identifica o tipo de pacote.
  * message_id: Identificador Único Universal (uuid) que identifica unicamente esse tipo de pacote.
    
4. **Resposta a verificação de pares ativos**: { "message_type": "Pong", "id": message_data["id"] }
  
  * message_type: string que identifica o tipo de pacote.
  * message_id: Uuid igual ao id do pacote do tipo "Pong".

5. **Confirmação de recebimento de mensagem**: { "message_type": "Ack", "message_id": message_id }
  * message_type: string que identifica o tipo de pacote.
  * message_id: lista com o endereço IP do remetente da mensagem e o timestamp atual responsavel por identificar unicamente o pacote e igual ao da mensagem recebida.

6. **Confirmação de exibição de mensagem**:  { "message_type": "Confirmed", "message_id": message_id }
  * message_type: string que identifica o tipo de pacote.
  * message_id: lista com o endereço IP do remetente da mensagem e o timestamp atual responsavel por identificar unicamente o pacote e igual ao da mensagem enviada.
   

### 2.3 - Threads
A aplicação foi contruída com base na operação de cinco Threads distintas, além da Thread principal, cada uma desempenhando um papel específico ao longo de toda a execução do sistema:

1. **receive_messages**: Tem a função primordial de receber todos os pacotes que chegam, adicionando-os a uma fila para processamento posterior.
2. **order_packages**: Opera em paralelo, porém em conjunto com a Thread `receive_messages`, sendo responsável por tratar os pacotes da fila, garantindo que todos os pacotes sejam processados corretamente.
3. **send_all_ping**: Responsável por enviar a todos os pares da lista de pares o pacote de verificação de pares ativos (Ping) a cada meio segundo.
4. **check_status**: Opera em paralelo, porém em conjunto com a Thread `send_all_ping`, sendo responsável por verificar a cada 0.2 segundos quis foram os pares que responderam ao "Ping" e atualizar seus respectivos status.
5. **remove_pending_messages**:  Opera em paralelo, porém em conjunto com a Thread `order_packages` e com a funcionalidade de enviar mensagens. Assim, sendo responsável por verificar se todos os pares ativos confirmaram o recebimento das mensagens, enviar a confirmação de exibição de mensagens e mover as mensagens confirmadas para a lista de exibição.

### 2.4 - Criptografia
A estratégia criptografica adotada foi a de deslocamento de caracteres. Também conhecida como cifra de César, é uma técnica de criptografia clássica que opera deslocando cada caractere em uma mensagem por um número fixo de posições no alfabeto. Essa abordagem foi escolhida após a tentativa (sem sucesso) de implementação de criptografia utilizando chaves pública-privada.

Ao implementar criptografia utilizando chaves pública-privada é necessário garantir que a troca de chaves entre os pares ocorra de maneira eficiente, eficaz e segura. Ou seja, é necessário garantir que todos os pares conheçam as chaves públicas dos usuários conectados aos sistema no momento que a mensagem chega. Por esse motivo, optou-se por reenviar a chave pública para todos os pares antes de cada pacote ser enviado, o que ocasionou erros relacionados a sincronização da lista de chaves, aumento expressivo do número de pacotes circulando na rede e baixas no desempenho do sistema como um todo.

Ao implementar a cifra de César, o software ganhou em desempenho e simplicidade, entretanto o sistema ficou bastante vulnerável a ataques, especialmente por meio de métodos de força bruta, devido ao pequeno espaço de chaves possíveis. 

# 3. Resultados
Ao iniciar o sistema, é solicitado do usuário o endereço IP da sua máquina na rede e a porta que deseja utilizar para a troca de mensagens (por ser um protótipo é necessário utilizar a porta 5555). Em seguida, é possível acessar um menu interativo com três opções: [1] para enviar mensagens, [2] para visualizar as mensagens recebidas e [3] para encerrar o aplicativo. Conforme a imagem abaixo:

![Menu principal.](https://github.com/bielcmoraes/Concorrencia-e-Conectividade-Problema-2/blob/master/readme_images/menu_principal.png)

É importante salientar que após a sincronização incial do sistema (a sincronização inicial é capaz de atualizar o timestamp do relógio lógico e recuperar as mensagens trocadas enquanto o usuário estivesse offline, desde que pelo menos um dos pares permanecesse ativo), uma nova sincronização é realizada a cada 5 segundos onde todos os pares ativos enviam sua lista de mensagens atual garantindo que todos tenham a mesma versão da conversa.

Por fim, é de suma importancia destacar a robustez e simplicidade do sistema desenvolvido, visto que cumpre com as principais exigências da startup contratante.

# 4. Conclusão
Durante a implementação desse sofware houve um contante desafio e esforço que contribuiram para o entendimento do funcionamento de sistemas distribuídos de maneira geral. É de suma importância para desenvolvedores entender aspectos inerentes a sincronização e os desafios e vantagens a cerca de algumas arquiteturas descentralizadas, especialmente a peer to peer.

Todos os principais requisitos foram cumpridos de maneira eficiente, em especial a ordenação das mensagens e a garantia de que as listas de mensagens são as mesmas para todos os usuários ativos. É possível encerrar o software e recuperar mensagens trocadas anteriormente, desde que pelo menos um dos pares tenha ficado "online" e todos os pacotes que circulam na rede são criptografados.

Pensando em possíveis melhorias, é interessante que, posteriormente, o sistema de criptografia seja atualizado com a implementação de criptografia de chave pública-privada ou com outra forma mais segura porém igualmente eficaz. Acredita-se que com essa simples melhoria a segurança do sistema como um todo melhore bastante.

# Referências
Python threading module: Disponível em: https://docs.python.org/3/library/threading.html. Acesso em: 20 de out. de 2023

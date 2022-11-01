import socket
import utils
from utils import States

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# initial server_state
server_state = States.CLOSED

# Build the UDP socket
sock = socket.socket(socket.AF_INET,    # Internet
                     socket.SOCK_DGRAM) # UDP

sock.bind((UDP_IP, UDP_PORT)) # wait for connection

# Some helper functions to keep the code clean and tidy
def update_server_state(new_state):
  global server_state
  if utils.DEBUG:
    print(server_state, '->', new_state) 
  server_state = new_state

# Receive a message and return header, body and addr
# addr is used to reply to the client
# this call is blocking
def recv_msg():
  data, addr = sock.recvfrom(1024)
  header = utils.bits_to_header(data)
  body = utils.get_body_from_data(data)
  return (header, body, addr)

# the server runs in an infinite loop and takes
# action based on current state and updates its state
# accordingly
# You will need to add more states, please update the possible
# states in utils.py file
while True:
  if server_state == States.CLOSED:
    # we already started listening, just update the state
    update_server_state(States.LISTEN)
  elif server_state == States.LISTEN:
    # we are waiting for a message
    header, body, addr = recv_msg()
    # if received message is a syn message, it's a connection initiation 
    if header.syn == 1:
      # Set the sequence to a random number 
      seq_number = utils.rand_int() 

      # ACK is the incoming header SEQ number + 1
      ack_number = header.seq_num + 1

      # Update server state to SYN_RECEIVED
      update_server_state(States.SYN_RECEIVED)

      ### sending message from the server:
      #   use the following method to send messages back to client
      #   addr is recieved when we receive a message from a client (see above)
      #   sock.sendto(your_header_object.bits(), addr)

  elif server_state == States.SYN_RECEIVED:
    # Received a SYN... Need to reply with a SYN_ACK

    # Create a header
    syn_ack_header = utils.Header(seq_number, ack_number, syn=1, ack=1, fin=1)

    print("Going to try to send to address: " + str(addr))

    # Send the syn ack
    # Can I do this here? Will I have access to the addr variable? Or do I send above 
    sock.sendto(syn_ack_header.bits(), addr)

    # Modify the state
    update_server_state(States.SYN_SENT)

  elif server_state == States.SYN_SENT:
    # Wait to receive an ack back from the client
    header, body, addr = recv_msg()

    # Check if the client replied with an ack
    if header.ack == 1:
      print("CLIENT REPLIED WITH ACK")
      update_server_state(States.ESTAB)
  elif server_state == States.ESTAB:
    # Variable to hold the entire message
    receivedMessage = ""

    # Need to receive messages until the state changes
    header, body, addr = recv_msg()
    
    # Check if there is a fin bit to end the connection
    if header.fin == 1:
      server_state = States.CLOSE_WAIT

      print("FINAL LOAED MESSAGE " +  receivedMessage)
      pass
    else:
      # No FIN bit, continue loading the message

      # Add the body of the TCP segment to the received message
      receivedMessage = receivedMessage + body
  elif server_state == States.CLOSE_WAIT:
    print("It is time to close wait")
  else:
    pass

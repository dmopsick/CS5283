import socket
from turtle import update
import utils
from utils import States

UDP_IP = "127.0.0.1"
# UDP_PORT = 5005 # For testing without channel
UDP_PORT = 5008 # For testing with channel

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

# Variable to hold the entire message
receivedMessage = ""

# the server runs in an infinite loop and takes
# action based on current state and updates its state
# accordingly
# You will need to add more states, please update the possible
# states in utils.py file
while True:
  if server_state == States.CLOSED:
    # Make sure the receivedMessage is initialized every time connection is established
    receivedMessage = ""

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
    syn_ack_header = utils.Header(seq_number, ack_number, syn=1, ack=1, fin=0)

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
      update_server_state(States.ESTAB)
  elif server_state == States.ESTAB:
    # Need to receive messages until the state changes
    header, body, addr = recv_msg()

    # If the end of message bit has been loaded, print the message 
    end_of_message_length = len(utils.END_OF_MESSAGE)

    # If the received message is long enough to contain an end of message sequence, check for it
    if len(receivedMessage) > end_of_message_length:
      # If the message currently ends with an end of message sequence, print the entire message
      if receivedMessage[-end_of_message_length:] == utils.END_OF_MESSAGE:
        print(receivedMessage)
    
    # Check if there is a fin bit to end the connection
    if header.fin == 1:
      # Load the received seq_num
      fin_seq_num = header.seq_num
      fin_ack_num = fin_seq_num + 1

      # Build the FIN ACK header
      fin_ack_header = utils.Header(0, fin_ack_num, syn=0, ack=1, fin=0)
      
      # Send the FIN ACK to the client
      sock.sendto(fin_ack_header.bits(), addr)

      update_server_state(States.CLOSE_WAIT)

      # Leaving this print to show the transferred message hard coded on fin, testing only
      # print("FINAL LOADED MESSAGE " +  receivedMessage)
    else:
      # No FIN bit, continue loading the message segment by segment

     #  print("Flag 1: Received following seq number: " + str(header.seq_num))

      # Get the sequence number of the received data
      data_seq_num = header.seq_num

      # Verify the seq numbers to determine whether the message is arriving in the corect order
      if (data_seq_num == len(receivedMessage)):
        # Based on seq number this is the next message, append it to the received message 

        # Add the body of the TCP segment to the received message
        receivedMessage = receivedMessage + body
      else :
        # This packet has arrived out of order... let's ignore for noq
        pass

      # Must send back an ack no matter what 
      # Build out the ack header
      data_transfer_ack_num = len(receivedMessage) + 1

      # print("Flag 2: Send back the ack " + str(data_transfer_ack_num))

      data_transfer_ack_header = utils.Header(seq_num=0, ack_num=data_transfer_ack_num, syn=0, ack=1, fin=0)

      # Send the header
      sock.sendto(data_transfer_ack_header.bits(), addr)

  elif server_state == States.CLOSE_WAIT:
    # Generate a sequence num
    seq_num = utils.rand_int()

    # Build a FIN header to send to the the client
    fin_header = utils.Header(seq_num, 0, syn=0, ack=0, fin=1)

    # Send the fin header to the client
    sock.sendto(fin_header.bits(), addr)

    # Update to LAST_ACK
    update_server_state(States.LAST_ACK)

  elif server_state == States.LAST_ACK:
    # Receive the final ack to finish the teardown
    header, body, addr = recv_msg()

    # Make sure the client as sent an ACK back
    if header.ack == 1:
    # Set state to closed, connection done, toredown, return server to closed
      update_server_state(States.CLOSED)

  else:
    pass

from multiprocessing import Value
from threading import Timer
from utils import States
import multiprocessing
import random
import socket
import time
import utils

UDP_IP = "127.0.0.1"
UDP_PORT = 5005 # Connecting without channel
# UDP_PORT = 5007 # Testing with channel
MSS = 12 # maximum segment size | This is measured in bytes
MSL = 5 # MAX SEGMENT LIFETIME -  Not sure what value it should be. I am measuring this in seconds for use with Python Time Library

def send_udp(message):
  sock.sendto(message, (UDP_IP, UDP_PORT))

class Client:
  def __init__(self):
    self.client_state = States.CLOSED
    self.handshake()

  def handshake(self):
    if self.client_state == States.CLOSED:
      seq_num = utils.rand_int()
      syn_header = utils.Header(seq_num, 0, syn = 1, ack = 0, fin=0)
      # for this case we send only header;
      # if you need to send data you will need to append it
      send_udp(syn_header.bits())

      self.update_state(States.SYN_SENT)

      # Initialize last received ack and seq num
      self.last_received_ack = -1
      self.last_received_seq_num = -1
      
      # Wait for response from syn_ack
      self.receive_acks()

      # print("Received ack " + str(self.last_received_ack))
      # print("Sent seq num " + str(seq_num))

      # Check if the received ack is equal to the sent seq_num + 1
      if self.last_received_ack == seq_num + 1:
        server_seq_num = self.last_received_seq_num 
        ack_num = server_seq_num + 1
        # I do not think ack needs a seq num
        # ack_seq_num = utils.rand_int()

        # Build the header to send the ACK
        ack_header = utils.Header(0, ack_num, syn=0, ack=1, fin=0)

        # Send the ACK
        send_udp(ack_header.bits())

        self.update_state(States.ESTAB)
    
    else:
      pass

  def terminate(self):

    # Can we only terminate an established connection? 
    if self.client_state == States.ESTAB:
      # Generate Seq num
      fin_seq_num = utils.rand_int()

      # Build Fin header to send
      fin_header = utils.Header(fin_seq_num, 0, syn=0, ack=0, fin=1)

      # Send the fin header
      send_udp(fin_header.bits())

      self.update_state(States.FIN_WAIT_1)

      # Wait to receive an ack
      self.last_received_ack = -1
      self.last_received_seq_num = -1
      self.receive_acks()
      
      # Verify the received ack_num
      if self.last_received_ack == fin_seq_num + 1: 
        self.update_state(States.FIN_WAIT_2)

        # Wait for the FIN from the sever
        self.receive_acks()

        # Load the received seq num
        server_fin_seq_num =  self.last_received_seq_num
        
        fin_ack_num = server_fin_seq_num + 1

        # Build a header to send an ACK back
        fin_ack_header = utils.Header(0, fin_ack_num, syn=0, ack=1, fin=0)

        # Send the ACK of the FIN to the server
        send_udp(fin_ack_header.bits())

        # Should the time wait be before the directly above sending of ACK? I think not based on the RFC diagram and slides
        # Here is where we can do a timed wait for twice the legth of the max segment life time (MSL)
        self.update_state(States.TIMED_WAIT)
        time.sleep(MSL * 2)

        # Close the connection
        self.update_state(States.CLOSED)

    else:
      # print("Terminate called, but not in ESTAB state")
      pass
     
  def update_state(self, new_state):
    if utils.DEBUG:
      print(self.client_state, '->', new_state)
    self.client_state = new_state

  def send_reliable_message(self, message):
    # print("Send Reliable message called with " + message)

    # Verify that the connection is established before we send the message
    if self.client_state == States.ESTAB:
      # send messages
      # we loop/wait until we receive all ack.

      # Going to treat each ASCII character as one byte    
      # Need to determine how much of the message has been sent
      charactersSent = 0

      # Iterate until the entire messae is sent
      while charactersSent  < len(message):
        # Build header for sending reliably
        # I will make characters sent the sequence number to allow the server to determine the correct order of the string
        transferHeader = utils.Header(charactersSent, 0, syn=0, ack=0, fin=0)
        
        # Build the portion of the body to send
        transferBody = message[charactersSent:charactersSent + MSS]

        # print("Raw text to send " + transferBody)

        # Convert the ascii text to bits
        transferBodyBits = transferBody.encode('ascii')

        # print('Bits to send ' + str(transferBodyBits))

        # Combine header and the body and send it
        send_udp(transferHeader.bits() + transferBodyBits)

        # Increment characters sent 
        charactersSent += MSS


  # these two methods/function can be used receive messages from
  # server. the reason we need such mechanism is `recv` blocking
  # and we may never recieve a package from a server for multiple
  # reasons.
  # 1. our message is not delivered so server cannot send an ack.
  # 2. server responded with ack but it's not delivered due to
  # a network failure.
  # these functions provide a mechanism to receive messages for
  # 1 second, then the client can decide what to do, like retransmit
  # if not all packets are acked.
  # you are free to implement any mechanism you feel comfortable
  # especially, if you have a better idea ;)
  def receive_acks_sub_process(self, s, lst_rec_ack_shared, lst_rec_seq_shared):
    if utils.DEBUG:
      print('subproc start in function')
    while True:
      recv_data, addr = s.recvfrom(1024)
      header = utils.bits_to_header(recv_data)
      if utils.DEBUG:
        print('received subproc header: ')
        print(header)
      if header.ack_num > lst_rec_ack_shared.value:
        lst_rec_ack_shared.value = header.ack_num
        if utils.DEBUG:
          print('subproc updated ack: ', lst_rec_ack_shared.value)
      if header.seq_num > lst_rec_seq_shared.value:
        lst_rec_seq_shared.value = header.seq_num
        if utils.DEBUG:
          print('subproc updated seq: ', lst_rec_seq_shared.value)

  def receive_acks(self):
    # Start receive_acks_sub_process as a process
    lst_rec_ack_shared = Value('i', self.last_received_ack)
    lst_rec_seq_shared = Value('i', self.last_received_seq_num)

    p = multiprocessing.Process(target=self.receive_acks_sub_process, args=(sock, lst_rec_ack_shared, lst_rec_seq_shared))
    p.start()
    # Wait for 1 seconds or until process finishes
    p.join(1)
    # If process is still active, we kill it
    if p.is_alive():
      p.terminate()
      p.join()
    # here you can update your client's instance variables.
    self.last_received_ack = lst_rec_ack_shared.value
    self.last_received_seq_num = lst_rec_seq_shared.value
    if utils.DEBUG:
      print('received: ', self.last_received_ack)
      print('shared variable: ', lst_rec_ack_shared)

# Need to have a main process to use the multi threading logic
if __name__ == "__main__":
  sock = socket.socket(socket.AF_INET,    # Internet
                     socket.SOCK_DGRAM) # UDP

  # we create a client, which establishes a connection
  client = Client()

  # we send a message
  client.send_reliable_message("The quick brown fox jumps over the lazy dog")

  # we terminate the connection
  client.terminate()

from email.policy import HTTP
import socket
import sys
import re
import os

CRLF = "\r\n\r\n"
socket.setdefaulttimeout = 0.50
os.environ['no_proxy'] = '127.0.0.1,localhost'

# Info of the server
serverName = 'localhost'
serverPort = 8080

# Take in arguments from CLI
destinationUrl = sys.argv[1]
httpMethod = sys.argv[2]

print(destinationUrl)
print(httpMethod)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.settimeout(0.30)

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
# set up TCP connection
s.connect((serverName, serverPort))

msg = "%s %s HTTP/1.1\r\nHost: %s%s" % (httpMethod, destinationUrl, serverName, CRLF)
# print("msg request: \n", msg)

# send HTTP get request
s.send(msg.encode())

dataAppend = ''

# wait for response from server
data = (s.recv(10000000))
if not data: print('error, no response')
else:
    dataAppend = dataAppend, repr(data)

    dataAppend = dataAppend[1].split(CRLF, 1)[0]

print(dataAppend)

import socket
import sys
from datetime import datetime
from urllib.parse import urlparse
import re
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# variables from the sample file
socket.setdefaulttimeout = 0.50
os.environ['no_proxy'] = '127.0.0.1,localhost'
linkRegex = re.compile('<a\s*href=[\'|"](.*?)[\'"].*?>')
CRLF = "\r\n\r\n"

# Fetch functionality to perform the actual GET and HEAD calls
def fetch(url, method):
    serverResponse = ''
    
    # Code taken from sample file
    url = urlparse(url)
    path = url.path
    # print(path)
    # print(url.netloc)

    if path == "":
        path = "/"
    HOST = url.netloc  # The remote host
    PORT = 80          # The same port as used by the server
    # create an INET, STREAMing socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # print(socket.AF_INET)
    # print(socket.SOCK_STREAM)
  
    s.settimeout(0.30)
  
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # set up TCP connection
    s.connect((HOST, PORT))
    
    msg = "%s %s HTTP/1.1\r\nHost: %s%s" % (method, path, HOST, CRLF)
    # print("msg request: \n", msg)
    
    # send HTTP get request
    s.send(msg.encode())

    # wait for response from server
    data = (s.recv(10000000))
    if not data: print('error, no response')
    else:
        serverResponse = serverResponse, repr(data)

    # shutdown and close tcp connection and socket
    s.shutdown(1)
    s.close()
    # print('Received', dataAppend)

    return serverResponse

# Load command line arguments
portNumString = sys.argv[1]
directory = sys.argv[2]

# Convert the argument to an int
portNum = int(portNumString)

serverName = 'localhost'
serverPort = portNum

print("The server is ready to receive...")

class MyServer(BaseHTTPRequestHandler):    

    # Make sure we are using HTTP/1.1
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        self.send_response(501)
        self.send_header("Content-type", "text/html")
        self.send_header("Host", serverName + ":" + str(portNum))
        self.end_headers()
        self.wfile.write(bytes("<html><body><h1>POST NOT SUPPORTED</h1></body></html>", "utf-8"))

    def do_GET(self):
        # Check if a path has been specified
        url = self.path

        if url == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(open("index.html", "r").read()))
            self.send_header("Host", serverName + ":" + str(portNum))
            self.end_headers()
            self.wfile.write(bytes(open("index.html", "r").read(), "utf-8"))
        # Ignore the favion.ico loads from Chrome that are spamming output for debugging
        elif url != "/favicon.ico":
            # Decode the path as the directory -- Drop the leading/
            destUrl = self.path[1:]
            # print("Flag 0 " + destUrl)

            httpResponse = fetch(destUrl, 'GET')

            headers = httpResponse[1].split(CRLF, 1)[0]

            request_line = headers.split('\\r\\n')[0]

            response_code = int(request_line.split(' ')[1])

            if (response_code == 200):
                # Load the body -- last element 
                rawResponse = headers.split('\\r\\n')[-1]
                httpResponseBody = "<html><body><div>" + rawResponse + "</div></body></html>"
                # print(httpResponseBody)
            elif (response_code == 404): 
                httpResponseBody = "<html><body><h1>404 - Page not found</h1><p>Unable to find a public file with path <b>" + destUrl + "</b>. Double check the address is correct.</p></body></html>"
            
            # Build the Response to send back to the client            
            self.send_response(response_code)

            self.send_header('Content-Length', len(httpResponseBody))
            self.send_header("Content-type", "text/html")
            self.send_header("Host", serverName + ":" + str(portNum))
            self.send_header('Date', str(datetime.now()))
            self.send_header('Server', 'Mopsick CS-5283 Server')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(bytes(httpResponseBody, "utf-8"))

    def do_HEAD(self):
        # Decode the path as the directory -- Drop the leading/
        destUrl = self.path[1:]
        # print("Flag 0 " + destUrl)

        httpResponse = fetch(destUrl, 'HEAD')

        headers = httpResponse[1].split(CRLF, 1)[0]

        request_line = headers.split('\\r\\n')[0]

        response_code = int(request_line.split(' ')[1])

        if (response_code == 200):
            # print(headers.split('\\r\\n'))
            contentLength = headers.split('\\r\\n')[6].split(' ')[1]
        
        # Build the Response to send back to the client            
        self.send_response(response_code)

        if response_code == 200:    
            self.send_header('Content-Length', contentLength)
        self.send_header("Content-type", "text/html")
        self.send_header("Host", serverName + ":" + str(portNum))
        self.send_header('Date', str(datetime.now()))
        self.send_header('Server', 'Mopsick CS-5283 Server')
        self.send_header('Connection', 'close')
        self.end_headers()

webServer = HTTPServer((serverName, serverPort), MyServer)
print("Server started http://%s:%s" % (serverName, serverPort))

try:
    webServer.serve_forever()
except KeyboardInterrupt:
    pass

webServer.server_close()
print("Server stopped.")    

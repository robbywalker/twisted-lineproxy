#
#  lineproxy_plugin.py
#  twisted-lineproxy
#
#  Copyright 2010 The phpserialize Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS-IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from zope.interface import implements

from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.internet import protocol, reactor, ssl
from twisted.protocols import basic
from twisted.python import usage
from twisted.plugin import IPlugin, log



class Options(usage.Options):
  """Options for this plugin."""

  optParameters = [
    ["port", "p", 1212, "The port number to listen on."],
    ["destination", "d", "imap.gmail.com", "The server to connect to."],
    ["destination_port", "P", 993, "The server port to connect to."],
    ["ssl", "s", True, "Whether to connect using SSL"]
  ]



class LineProxyClient(basic.LineReceiver):
  """Protocol for a line proxy client."""

  factory = None

  def connectionMade(self):
    """Called when the connection to the remote server is complete."""
    log.msg("Connection to client made")
    self.factory.server.setClient(self)


  def lineReceived(self, line):
    """Forwards lines from the remote connection to the incoming connection."""
    log.msg("S: %s" % line)
    self.factory.server.sendLine(line)


  def connectionLost(self, _):
    """Logs the connection failure and closes the incoming connection."""
    self.factory.server.transport.loseConnection()



class LineProxyClientFactory(protocol.ClientFactory):
  """Factory for a line proxy client."""

  protocol = LineProxyClient


  def __init__(self, server):
    self.server = server



class LineProxyServerProtocol(basic.LineReceiver):
  """Protocol for a line proxy server."""

  options = {}

  client = None


  def setClient(self, client):
    """Sets the client object used to communicate with the remote server."""
    self.client = client


  def connectionMade(self):
    """When a server connection is made, connect to the remote server."""
    destination = self.options["destination"]
    destinationPort = self.options["destination_port"]
    log.msg("Connecting to %s:%d" % (destination, destinationPort))
    factory = LineProxyClientFactory(self)
    if self.options["ssl"]:
      sslFactory = ssl.ClientContextFactory()
      sslFactory.method = ssl.SSL.TLSv1_METHOD
      reactor.connectSSL(destination,
                         destinationPort,
                         factory,
                         sslFactory)
    else:
      reactor.connectTCP(destination,
                         destinationPort,
                         factory)


  def lineReceived(self, line):
    """Incoming lines are forwarded to the remote server."""
    log.msg("C: %s" % line)
    self.client.sendLine(line)



class LineProxyFactory(protocol.ServerFactory):
  """Factory for a line proxy server."""

  protocol = LineProxyServerProtocol

  def __init__(self, options):
    self.options = options

  def buildProtocol(self, addr):
    """Prepares the proxy protocol object."""
    p = protocol.ServerFactory.buildProtocol(self, addr)
    p.options = self.options
    return p



class LineProxyMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "lineproxy"
    description = "Proxies a server that communicates in lines."
    options = Options

    def makeService(self, options):
      """Construct a TCPServer from a factory defined in myproject."""
      return internet.TCPServer(int(options["port"]), LineProxyFactory(options))


serviceMaker = LineProxyMaker()
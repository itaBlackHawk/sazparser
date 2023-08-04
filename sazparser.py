from zipfile import ZipFile
from xml.dom.minidom import parse, parseString
from isodate import parse_datetime
from io import StringIO


class SazFile:
	class ParseError(Exception):
		pass
	
	def __init__(self, filename):
		self.filename = filename
		self._zipfile = None
		self._sessions = []
		self._cfilelist = []
		self._mfilelist = []
		self._sfilelist = []
		self._session_num = 0
	
	@property
	def zipfile(self):
		if self._zipfile is None:
			self._zipfile = ZipFile(self.filename)
		return self._zipfile
	
	@property
	def cfilelist(self):
		if not self._cfilelist:
			self._cfilelist = [
				x for x in self.zipfile.namelist()
				if x.startswith('raw') and x.endswith('_c.txt')
			]
		return self._cfilelist
	
	@property
	def mfilelist(self):
		if not self._mfilelist:
			self._mfilelist = [
				x for x in self.zipfile.namelist()
				if x.startswith('raw') and x.endswith('xml')
			]
		return self._mfilelist
	
	@property
	def sfilelist(self):
		self._sfilelist = [
				x for x in self.zipfile.namelist()
				if x.startswith('raw') and x.endswith('_s.txt')
			]
		return self._sfilelist
	
	@property
	def html(self):
		fname = '_index.htm'
		return self.zipfile.read(fname).decode('utf-8')
	
	@property
	def content_type(self):
		pass
	
	@property
	def session_num(self):
		if self._session_num == 0:
			clen = len(self.cfilelist)
			mlen = len(self.mfilelist)
			slen = len(self.sfilelist)
	
			if not (clen == mlen == slen):
				raise self.ParseError('files missing')
	
			self._session_num = clen
	
		return self._session_num
	
	@property
	def sessions(self):
		if self._sessions == []:
			for i in range(self.session_num):
				rawdata = {
					"c": self.zipfile.read(self.cfilelist[i]),
					"m": self.zipfile.read(self.mfilelist[i]),
					"s": self.zipfile.read(self.sfilelist[i]),
				}
				session = Session(rawdata)
				self._sessions.append(session)
	
		return self._sessions
	
	@property
	def sequence_time(self):
		starttime = min([
			parse_datetime(s.timing['ClientBeginRequest'])
			for s in self.sessions
			if str(parse_datetime(s.timing['ClientBeginRequest'])) != '0001-01-01 00:00:00'
		])
	
		endtime = max([
			parse_datetime(s.timing['ClientDoneResponse'])
			for s in self.sessions
			if str(parse_datetime(s.timing['ClientDoneResponse'])) != '0001-01-01 00:00:00'
		])
	
		return (endtime - starttime).total_seconds()
	
	
class Session:
	def __init__(self, rawdata):
		self._rawdata = rawdata
		self._crequest = None
		self._srequest = None
		self._metadata = None
	
	@property
	def client_request(self):
		if self._crequest is None:
			self._crequest = ClientRequest(self._rawdata['c'])
	
		return self._crequest
	
	@property
	def server_request(self):
		if self._srequest is None:
			self._srequest = ServerRequest(self._rawdata['s'])
	
		return self._srequest
	
	@property
	def metadata(self):
		if self._metadata is None:
			self._metadata = MetaData(self._rawdata['m'])
	
		return self._metadata
	
	@property
	def timing(self):
		return self.metadata.timing
	
	@property
	def is_static(self):
		return self.server_request.content_type in [
			b'image/png', b'image/gif', b'text/javascript', b'text/css'
		]
	
	@property
	def https_handshake_time(self):
		return int(self.timing['HTTPSHandshakeTime'])
	
	@property
	def tcp_connec_time(self):
		return int(self.timing['TCPConnectTime'])
	
	@property
	def dns_time(self):
		return int(self.timing['DNSTime'])
	
	@property
	def gateway_time(self):
		return int(self.timing['GatewayTime'])
	
	@property
	def server_time(self):
		ret = 0
		starttime = parse_datetime(self.timing['ServerGotRequest'])
		endtime = parse_datetime(self.timing['ServerBeginResponse'])
	
		if not (str(starttime) == '0001-01-01 00:00:00' \
			or str(endtime) == '0001-01-01 00:00:00'):
			ret = (endtime - starttime).total_seconds()
			ret = 0 if ret < 0 else ret
	
		return ret
	
	@property
	def download_time(self):
		ret = 0
		starttime = parse_datetime(self.timing['ServerBeginResponse'])
		endtime = parse_datetime(self.timing['ClientDoneResponse'])
	
		if not (str(starttime) == '0001-01-01 00:00:00' \
			or str(endtime) == '0001-01-01 00:00:00'):
			ret = (endtime - starttime).total_seconds()
			ret = 0 if ret < 0 else ret
	
		return ret

class InfoBase:
	def __init__(self, rawdata):
		self._rawdata = rawdata
	

class Request(InfoBase):
	def __init__(self, rawdata):
		super(Request, self).__init__(rawdata)
		self._message = ''
		self._headers = {}
		self._body = None
	
	@property
	def message(self):
		if not self._message:
			self._message = self._rawdata.split(b'\r\n')[0]
		return self._message
	
	@property
	def headers(self):
		if not self._headers:
			self._headers = {
				h.split(b':')[0].strip().decode('utf-8').lower(): h.split(b':', 1)[1].strip().strip().decode('utf-8').lower()
				for h in self._rawdata.split(b'\r\n\r\n')[0].split(b'\r\n')[1:]
			}
		return self._headers
	
	@property
	def body(self):
		if self._body is None:
			# splitting the header from the rest od the data
			self._body = self._rawdata.split(b'\r\n\r\n', 1)[1]
			try:
				# if there was a chunked transfer, we need to recontruct the real body
				if self.headers.get('transfer-encoding') == 'chunked':
					buffer = b''
					while True:
						line = self._body.split(b'\r\n', 1)[0]
						chunk_length = int(line, 16)
						if chunk_length != 0:
							buffer += self._body.split(b'\r\n', 1)[1][:chunk_length]
							# Each chunk is followed by an additional empty newline ( \r\n ) so adding 2 to take care of that
							self._body = self._body.split(b'\r\n', 1)[1][chunk_length+2:]

						# Finally, a chunk size of 0 is an end indication
						if chunk_length == 0:
							break

					self._body = buffer
				# decompress gzip data
				# TODO: add other methods
				if self.headers.get('content-encoding') == 'gzip':
					self._body = zlib.decompress(self._body, 16+zlib.MAX_WBITS)
			except KeyError:
				pass
		return self._body


class ClientRequest(Request):
	@property
	def method(self):
		return self.message.split(b' ')[0]


class ServerRequest(Request):
	@property
	def status(self):
		return self.message.split(b' ')[1]
	
	@property
	def content_type(self):
		ret = None
		try:
			ret = self.headers[b'Content-Type'].split(b';')[0].strip()
		except KeyError:
			pass
		return ret


class MetaData(InfoBase):
	def __init__(self, rawdata):
		super(MetaData, self).__init__(rawdata)
		self._timing = {}
	
	@property
	def timing(self):
		if not self._timing:
			dom = parseString(self._rawdata.decode('utf-8-sig'))
			item = dom.getElementsByTagName('SessionTimers')[0]
	
			for key in item.attributes.keys():
				self._timing[key] = item.attributes[key].value
	
		return self._timing


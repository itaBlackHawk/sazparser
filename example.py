from sazparser import SazFile

def main():
	import argparse
	parser = argparse.ArgumentParser(description='saz file parser')
	parser.add_argument('filename', help='saz file name')
	args = parser.parse_args()
	
	sazfile = SazFile(args.filename)
	static_count, server_time, dserver_time = 0, 0.0, 0.0
	download_time, ddownload_time = 0.0, 0.0
	dns_time, tcp_connec_time, https_handshake_time, gateway_time = 0, 0, 0, 0
	ddns_time, dtcp_connec_time, dhttps_handshake_time, dgateway_time = 0, 0, 0, 0
	for num, session in enumerate(sazfile.sessions):
		if session.is_static:
			static_count += 1
			server_time += session.server_time
			download_time += session.download_time
			dns_time += session.dns_time
			tcp_connec_time += session.tcp_connec_time
			https_handshake_time += session.https_handshake_time
			gateway_time += session.gateway_time
		else:
			dserver_time += session.server_time
			ddownload_time += session.download_time
			ddns_time += session.dns_time
			dtcp_connec_time += session.tcp_connec_time
			dhttps_handshake_time += session.https_handshake_time
			dgateway_time += session.gateway_time
	print(
		"{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8},{:8}".format(
			sazfile.session_num,
			static_count,
			round(server_time, 2),
			round(dserver_time, 2),
			round(download_time, 2),
			round(ddownload_time, 2),
			dns_time, ddns_time,
			tcp_connec_time, dtcp_connec_time,
			https_handshake_time, dhttps_handshake_time,
			gateway_time, dgateway_time,
		)
	)


if __name__ == '__main__':
    main()
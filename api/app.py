from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)

            # TODO: 接入 pricelib 进行真实计算
            # 接收由前方动态传递的参数，不要在此处硬编码海外指数等数据源
            # pv, greeks = calculate_price(params)
            
            # 模拟返回结构
            response_data = {
                "code": 0,
                "data": {
                    "pv": 10.5,
                    "greeks": {
                        "delta": 0.5, "gamma": 0.1, "vega": 0.2, "theta": -0.05, "rho": 0.03
                    }
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"code": -1, "msg": str(e)}).encode('utf-8'))

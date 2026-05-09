from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

from pricelib import VanillaOption, CallPut, ExerciseType

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

            # 解析前端传递的参数
            s = float(params.get("s", 100))
            strike = float(params.get("strike", 100))
            maturity = float(params.get("maturity", 1))
            r = float(params.get("r", 3)) / 100.0  # 转换为小数
            q = float(params.get("q", 0)) / 100.0   # 转换为小数
            vol = float(params.get("vol", 15)) / 100.0  # 转换为小数
            
            # 解析期权类型和行权方式
            callput_str = params.get("callput", "Call")
            exercise_type_str = params.get("exercise_type", "European")
            
            callput_enum = CallPut.Call if callput_str == "Call" else CallPut.Put
            exercise_type_enum = ExerciseType.European if exercise_type_str == "European" else ExerciseType.American

            # 使用 pricelib 进行真实计算
            option = VanillaOption(
                s=s,
                strike=strike,
                maturity=maturity,
                r=r,
                q=q,
                vol=vol,
                callput=callput_enum,
                exercise_type=exercise_type_enum,
            )
            result = option.pv_and_greeks()

            # 构建响应数据
            response_data = {
                "code": 0,
                "data": {
                    "pv": result.get("pv", 0),
                    "greeks": {
                        "delta": result.get("delta", 0),
                        "gamma": result.get("gamma", 0),
                        "vega": result.get("vega", 0),
                        "theta": result.get("theta", 0),
                        "rho": result.get("rho", 0)
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